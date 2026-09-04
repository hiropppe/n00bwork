"""B_worker: NDJSON ループ本体。

- 起動直後に hello を送る。
- stdin を1行=1メッセージで read し続ける（NDJSON）。
- 命綱: 親 A が死ぬと stdin が閉じ、for ループが EOF で抜けて自然終了する。
- b_core の import はこのプロセス内でのみ行う（A には import させない）。
- stdout は結果チャネル専用。ログ・例外は stderr に流す。

frozen（PyInstaller）でも dev（python worker.py）でも同じ挙動になるよう、
b_core を import できるパスを起動時に整える。
"""

from __future__ import annotations

import json
import os
import sys

# --- import パス解決 -------------------------------------------------------
# dev 実行時（python subsystem_b/worker.py）は、このファイルの隣の b_core を
# import できるよう sys.path に自分のディレクトリを足す。
# frozen 時は PyInstaller が b_core を同梱するのでこの追加は無害。
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from b_core import stats  # noqa: E402  （パス調整後に import する必要がある）

PROTOCOL_VERSION = 1
CAPABILITIES = ["stats.compute"]


def emit(obj: dict) -> None:
    """1 メッセージを stdout に1行で書き、必ず flush する。

    flush を忘れると A 側が結果を受け取れずハングするので必須。
    """
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def log(msg: str) -> None:
    """人間向けログ。stdout を汚さないよう stderr に流す。"""
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def emit_error(req_id, code: str, message: str) -> None:
    emit({"type": "response", "id": req_id, "error": {"code": code, "message": message}})


def handle_request(msg: dict) -> None:
    req_id = msg.get("id")
    method = msg.get("method")
    try:
        if method == "stats.compute":
            params = msg.get("params") or {}
            result = stats.compute(params.get("values"))
            emit({"type": "response", "id": req_id, "result": result})
        else:
            emit_error(req_id, "UNKNOWN_METHOD", f"unknown method: {method!r}")
    except stats.BadInputError as e:
        emit_error(req_id, "BAD_INPUT", str(e))
    except Exception as e:  # worker 自体は落とさない
        log(f"internal error handling request {req_id!r}: {e!r}")
        emit_error(req_id, "INTERNAL", str(e))


def main() -> int:
    # ハンドシェイク: 最初に自分の情報を1行出す。
    emit(
        {
            "type": "hello",
            "protocol_version": PROTOCOL_VERSION,
            "worker": "b_worker",
            "capabilities": CAPABILITIES,
        }
    )

    # 命綱: 親が死ぬと stdin が閉じ、この for ループが EOF で自然終了する。
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            emit_error(None, "PARSE_ERROR", f"invalid json: {e}")
            continue

        msg_type = msg.get("type")
        if msg_type == "shutdown":
            log("received shutdown, exiting")
            break
        elif msg_type == "request":
            handle_request(msg)
        else:
            # 未知の type は無視（ログのみ）
            log(f"ignoring message with unknown type: {msg_type!r}")

    # ループを抜けた = EOF or shutdown → プロセス終了
    return 0


if __name__ == "__main__":
    sys.exit(main())
