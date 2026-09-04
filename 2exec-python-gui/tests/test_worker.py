"""worker.py を実際に subprocess 起動し、request → response を検証する結合テスト。

B のロジック（stats.compute / numpy）との結合を確認する。
"""

from __future__ import annotations

import json

from conftest import WorkerProcess


def test_hello_first(worker_py_exec):
    with WorkerProcess(worker_py_exec) as w:
        hello = json.loads(w.recv())
        assert hello["type"] == "hello"
        assert hello["protocol_version"] == 1
        assert "stats.compute" in hello["capabilities"]


def test_stats_compute(worker_py_exec):
    with WorkerProcess(worker_py_exec) as w:
        json.loads(w.recv())  # hello を捨てる
        w.send(json.dumps({"type": "request", "id": "r1", "method": "stats.compute",
                           "params": {"values": [1, 2, 3, 4]}}))
        resp = json.loads(w.recv())
        assert resp["type"] == "response"
        assert resp["id"] == "r1"
        r = resp["result"]
        assert r["mean"] == 2.5
        assert r["min"] == 1
        assert r["max"] == 4
        assert r["median"] == 2.5
        assert abs(r["std"] - 1.1180339887) < 1e-6


def test_unknown_method(worker_py_exec):
    with WorkerProcess(worker_py_exec) as w:
        json.loads(w.recv())
        w.send(json.dumps({"type": "request", "id": "r2", "method": "nope", "params": {}}))
        resp = json.loads(w.recv())
        assert resp["error"]["code"] == "UNKNOWN_METHOD"


def test_bad_input_empty(worker_py_exec):
    with WorkerProcess(worker_py_exec) as w:
        json.loads(w.recv())
        w.send(json.dumps({"type": "request", "id": "r3", "method": "stats.compute",
                           "params": {"values": []}}))
        resp = json.loads(w.recv())
        assert resp["error"]["code"] == "BAD_INPUT"


def test_bad_input_non_numeric(worker_py_exec):
    with WorkerProcess(worker_py_exec) as w:
        json.loads(w.recv())
        w.send(json.dumps({"type": "request", "id": "r4", "method": "stats.compute",
                           "params": {"values": [1, "x", 3]}}))
        resp = json.loads(w.recv())
        assert resp["error"]["code"] == "BAD_INPUT"


def test_parse_error(worker_py_exec):
    with WorkerProcess(worker_py_exec) as w:
        json.loads(w.recv())
        w.send("this is not json")
        resp = json.loads(w.recv())
        assert resp["error"]["code"] == "PARSE_ERROR"


def test_multiple_requests_keep_ids(worker_py_exec):
    with WorkerProcess(worker_py_exec) as w:
        json.loads(w.recv())
        for i in range(3):
            w.send(json.dumps({"type": "request", "id": f"m{i}", "method": "stats.compute",
                               "params": {"values": [i, i + 1]}}))
            resp = json.loads(w.recv())
            assert resp["id"] == f"m{i}"


def test_shutdown_exits_cleanly(worker_py_exec):
    with WorkerProcess(worker_py_exec) as w:
        json.loads(w.recv())
        w.send(json.dumps({"type": "shutdown"}))
        assert w.proc.wait(timeout=5) == 0
