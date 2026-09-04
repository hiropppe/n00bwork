"""プロトコル（NDJSON メッセージの encode/decode、エラー形）のテスト。

B のロジック（numpy）には依存しない純粋なメッセージ形の検証。
"""

import json


def encode(obj: dict) -> bytes:
    return (json.dumps(obj) + "\n").encode("utf-8")


def decode_lines(data: bytes) -> list[dict]:
    return [json.loads(line) for line in data.split(b"\n") if line.strip()]


def test_request_roundtrip():
    msg = {
        "type": "request",
        "id": "abc",
        "method": "stats.compute",
        "params": {"values": [1, 2, 3]},
    }
    line = encode(msg)
    assert line.endswith(b"\n")
    (decoded,) = decode_lines(line)
    assert decoded == msg


def test_multiple_messages_split_on_newline():
    data = encode({"type": "request", "id": "1"}) + encode({"type": "request", "id": "2"})
    msgs = decode_lines(data)
    assert [m["id"] for m in msgs] == ["1", "2"]


def test_hello_shape():
    hello = {
        "type": "hello",
        "protocol_version": 1,
        "worker": "b_worker",
        "capabilities": ["stats.compute"],
    }
    (decoded,) = decode_lines(encode(hello))
    assert decoded["type"] == "hello"
    assert decoded["protocol_version"] == 1
    assert "stats.compute" in decoded["capabilities"]


def test_error_response_shape():
    resp = {
        "type": "response",
        "id": "abc",
        "error": {"code": "BAD_INPUT", "message": "values must be numbers"},
    }
    (decoded,) = decode_lines(encode(resp))
    assert decoded["error"]["code"] == "BAD_INPUT"


def test_success_response_shape():
    resp = {
        "type": "response",
        "id": "abc",
        "result": {"mean": 2.5, "std": 1.118, "min": 1, "max": 4, "median": 2.5},
    }
    (decoded,) = decode_lines(encode(resp))
    assert set(decoded["result"]) == {"mean", "std", "min", "max", "median"}


def test_blank_lines_are_ignored():
    data = b"\n\n" + encode({"type": "shutdown"}) + b"\n"
    msgs = decode_lines(data)
    assert msgs == [{"type": "shutdown"}]
