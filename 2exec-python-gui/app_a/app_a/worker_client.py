"""B_worker の起動・IPC・ライフサイクル管理。

QProcess を使い、GUI イベントループを絶対にブロックしない（非同期）。
呼び出し側は request() でリクエストを投げ、シグナルで結果を受け取る。

責務:
- 起動: QProcess で B を spawn。env をサニタイズ（frozen の _MEIPASS /
  LD_LIBRARY_PATH / DYLD_LIBRARY_PATH を子に継承させない）。
- 送信: request()。id を採番し JSON を1行書く。
- 受信: readyReadStandardOutput で stdout をバッファリング、改行で分割 →
  JSON parse → id で待ち側にディスパッチ。
- ハンドシェイク: 最初の hello で protocol_version を検証。
- 監督: finished / errorOccurred で B の死を検知して通知。
- 終了: shutdown() で shutdown 送信 → waitForFinished → terminate → kill。
"""

from __future__ import annotations

import json
import uuid

from PySide6.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    QTimer,
    Signal,
)

from . import paths

PROTOCOL_VERSION = 1

# 子に継承させたくない環境変数（frozen の A が同梱するライブラリを B が
# 掴んで壊れるのを防ぐ）。
_SANITIZE_ENV_KEYS = (
    "_MEIPASS",
    "_MEIPASS2",
    "LD_LIBRARY_PATH",
    "DYLD_LIBRARY_PATH",
    "DYLD_FRAMEWORK_PATH",
    "DYLD_FALLBACK_LIBRARY_PATH",
    "PYTHONPATH",
    "PYTHONHOME",
)


def _clean_env() -> QProcessEnvironment:
    env = QProcessEnvironment.systemEnvironment()
    for k in _SANITIZE_ENV_KEYS:
        env.remove(k)
    return env


class WorkerClient(QObject):
    """B_worker と 1:1 で対話するクライアント。

    Signals:
        ready(): hello を受けてプロトコル検証に成功した。
        result(id: str, result: dict): request の成功レスポンス。
        error(id: str, code: str, message: str): request の失敗レスポンス。
        worker_failed(message: str): B の起動失敗 / 異常終了 / プロトコル不整合。
        worker_finished(): B が正常に終了した。
    """

    ready = Signal()
    result = Signal(str, dict)
    error = Signal(str, str, str)
    worker_failed = Signal(str)
    worker_finished = Signal()

    def __init__(self, request_timeout_ms: int = 10000, parent: QObject | None = None):
        super().__init__(parent)
        self._proc = QProcess(self)
        self._buffer = bytearray()
        self._handshaked = False
        self._shutting_down = False
        self._request_timeout_ms = request_timeout_ms
        # id -> QTimer（タイムアウト管理）
        self._pending: dict[str, QTimer] = {}

        self._proc.setProcessEnvironment(_clean_env())
        # stdout=結果チャネル / stderr=ログ を分離して扱う
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(self._on_error_occurred)

    # --- ライフサイクル ---------------------------------------------------

    def start(self) -> None:
        """B_worker を起動する。"""
        exe = paths.worker_executable()

        if paths.is_frozen():
            program = str(exe)
            args: list[str] = []
        else:
            # dev: B の venv の python で worker.py を起動する
            py = paths.dev_worker_python()
            if py is None:
                # フォールバック（numpy が無いと B が import に失敗する点に注意）
                import sys as _sys

                program = _sys.executable
            else:
                program = str(py)
            args = [str(exe)]

        self._proc.setProgram(program)
        self._proc.setArguments(args)
        self._proc.start()

    def shutdown(self, wait_ms: int = 3000) -> None:
        """B を正常終了させる。shutdown → 待つ → terminate → kill の3段。"""
        self._shutting_down = True
        if self._proc.state() == QProcess.ProcessState.NotRunning:
            return

        # 1. shutdown メッセージ
        self._write({"type": "shutdown"})
        self._proc.closeWriteChannel()  # stdin を閉じる（EOF 自死の後押し）

        # 2. 待つ
        if self._proc.waitForFinished(wait_ms):
            return

        # 3. terminate → kill
        self._proc.terminate()
        if not self._proc.waitForFinished(1000):
            self._proc.kill()
            self._proc.waitForFinished(1000)

    # --- 送信 -------------------------------------------------------------

    def request(self, method: str, params: dict) -> str:
        """リクエストを送り、採番した id を返す。結果は result/error シグナルで届く。"""
        req_id = uuid.uuid4().hex
        self._write({"type": "request", "id": req_id, "method": method, "params": params})

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._on_timeout(req_id))
        timer.start(self._request_timeout_ms)
        self._pending[req_id] = timer
        return req_id

    def _write(self, obj: dict) -> None:
        if self._proc.state() != QProcess.ProcessState.Running:
            return
        data = (json.dumps(obj) + "\n").encode("utf-8")
        self._proc.write(data)

    # --- 受信 -------------------------------------------------------------

    def _on_stdout(self) -> None:
        self._buffer.extend(bytes(self._proc.readAllStandardOutput()))
        while True:
            idx = self._buffer.find(b"\n")
            if idx < 0:
                break
            line = bytes(self._buffer[:idx])
            del self._buffer[: idx + 1]
            line = line.strip()
            if not line:
                continue
            self._dispatch_line(line)

    def _on_stderr(self) -> None:
        # B のログ。ここでは握りつぶさず、標準エラーに素通しする。
        data = bytes(self._proc.readAllStandardError())
        if data:
            import sys as _sys

            _sys.stderr.write(data.decode("utf-8", errors="replace"))
            _sys.stderr.flush()

    def _dispatch_line(self, line: bytes) -> None:
        try:
            msg = json.loads(line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.worker_failed.emit(f"received unparsable line from worker: {e}")
            return

        msg_type = msg.get("type")
        if msg_type == "hello":
            self._handle_hello(msg)
        elif msg_type == "response":
            self._handle_response(msg)
        # それ以外は無視

    def _handle_hello(self, msg: dict) -> None:
        version = msg.get("protocol_version")
        if version != PROTOCOL_VERSION:
            self.worker_failed.emit(
                f"protocol version mismatch: worker={version}, expected={PROTOCOL_VERSION}"
            )
            # 互換性が無い worker とは対話しない
            self.shutdown()
            return
        self._handshaked = True
        self.ready.emit()

    def _handle_response(self, msg: dict) -> None:
        req_id = msg.get("id")
        # タイムアウトタイマを解除
        timer = self._pending.pop(req_id, None)
        if timer is not None:
            timer.stop()

        if "error" in msg and msg["error"] is not None:
            err = msg["error"]
            self.error.emit(req_id or "", err.get("code", "INTERNAL"), err.get("message", ""))
        else:
            self.result.emit(req_id or "", msg.get("result") or {})

    def _on_timeout(self, req_id: str) -> None:
        timer = self._pending.pop(req_id, None)
        if timer is not None:
            timer.stop()
        self.error.emit(req_id, "TIMEOUT", "worker did not respond in time")

    # --- 監督 -------------------------------------------------------------

    def _on_finished(self, exit_code: int, exit_status) -> None:
        # 残った pending をすべて失敗にする
        for req_id, timer in list(self._pending.items()):
            timer.stop()
            self.error.emit(req_id, "WORKER_GONE", "worker terminated")
        self._pending.clear()

        if self._shutting_down:
            self.worker_finished.emit()
        else:
            self.worker_failed.emit(f"worker exited unexpectedly (code={exit_code})")

    def _on_error_occurred(self, error) -> None:
        if self._shutting_down:
            return
        self.worker_failed.emit(f"worker process error: {error}")
