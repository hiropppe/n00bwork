"""エントリポイント。

QApplication 生成 → WorkerClient 起動 → MainWindow 表示 →
aboutToQuit に shutdown フックを接続（正常終了時に B を確実に落とす）。
"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .worker_client import WorkerClient


def _run_smoke() -> int:
    """APP_A_SMOKE=1 のときの非 GUI スモークテスト。

    frozen バイナリでもパス解決・env サニタイズ・IPC を検証できるよう、
    ウィンドウを出さずに B を起動し stats.compute を1周して終了コードを返す。
    """
    from PySide6.QtCore import QTimer

    app = QApplication(sys.argv)
    client = WorkerClient()
    state = {"ok": False, "err": None}

    def on_ready():
        client.request("stats.compute", {"values": [1, 2, 3, 4]})

    def on_result(req_id, result):
        state["ok"] = result.get("mean") == 2.5
        client.shutdown()
        QTimer.singleShot(0, app.quit)

    def fail(msg):
        state["err"] = msg
        QTimer.singleShot(0, app.quit)

    client.ready.connect(on_ready)
    client.result.connect(on_result)
    client.error.connect(lambda i, c, m: fail(f"{c}: {m}"))
    client.worker_failed.connect(fail)
    QTimer.singleShot(15000, lambda: fail("timeout"))

    client.start()
    app.exec()

    if state["ok"] and state["err"] is None:
        print("[smoke] PASS", flush=True)
        return 0
    print(f"[smoke] FAIL: {state['err']}", flush=True)
    return 1


def main() -> int:
    if os.environ.get("APP_A_SMOKE") == "1":
        return _run_smoke()


    app = QApplication(sys.argv)

    client = WorkerClient()
    # 正常終了時: shutdown 送信 → 待つ → terminate → kill（命綱の第1層）
    app.aboutToQuit.connect(client.shutdown)

    window = MainWindow(client)
    window.show()

    client.start()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
