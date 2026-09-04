"""dev 実行での A→B IPC 疎通スモークテスト（GUI は表示しない）。

QApplication を offscreen で立て、WorkerClient で B を起動し、hello 検証 →
stats.compute リクエスト → 結果受信 → shutdown までを1周する。
    QT_QPA_PLATFORM=offscreen .venv/bin/python smoke_ipc.py
"""

import sys

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtWidgets import QApplication

from app_a.worker_client import WorkerClient

app = QApplication(sys.argv)
client = WorkerClient()

state = {"ok": False, "err": None}


def on_ready():
    print("[smoke] worker ready, sending request")
    client.request("stats.compute", {"values": [1, 2, 3, 4]})


def on_result(req_id, result):
    print(f"[smoke] result: {result}")
    assert result["mean"] == 2.5
    assert result["max"] == 4
    state["ok"] = True
    client.shutdown()
    QTimer.singleShot(0, app.quit)


def on_error(req_id, code, message):
    state["err"] = f"{code}: {message}"
    print(f"[smoke] error: {state['err']}")
    QTimer.singleShot(0, app.quit)


def on_failed(message):
    state["err"] = message
    print(f"[smoke] worker failed: {message}")
    QTimer.singleShot(0, app.quit)


client.ready.connect(on_ready)
client.result.connect(on_result)
client.error.connect(on_error)
client.worker_failed.connect(on_failed)

# 安全弁: 10秒で強制終了
QTimer.singleShot(10000, lambda: (state.__setitem__("err", "timeout"), app.quit()))

client.start()
app.exec()

if state["ok"] and state["err"] is None:
    print("[smoke] PASS")
    sys.exit(0)
else:
    print(f"[smoke] FAIL: {state['err']}")
    sys.exit(1)
