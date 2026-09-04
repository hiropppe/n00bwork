"""命綱の検証: 親死亡で子が孤児にならず消えるか。

- 正常終了: shutdown で B が終わるか。
- stdin-EOF: stdin を閉じる（親の死を模擬）と B が EOF で自然終了するか。
- 強制 kill: 親経由で B を起動し、親を kill → B が stdin-EOF で消えるか。
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from conftest import WORKER_PY, WorkerProcess


def _alive(proc: subprocess.Popen) -> bool:
    return proc.poll() is None


def test_shutdown_message_terminates(worker_py_exec):
    with WorkerProcess(worker_py_exec) as w:
        json.loads(w.recv())  # hello
        w.send(json.dumps({"type": "shutdown"}))
        assert w.proc.wait(timeout=5) == 0


def test_stdin_eof_self_death(worker_py_exec):
    """stdin を閉じる = 親が死んでパイプが閉じた状況。B は EOF で自然終了する。"""
    with WorkerProcess(worker_py_exec) as w:
        json.loads(w.recv())  # hello
        w.close_stdin()
        assert w.proc.wait(timeout=5) == 0


def test_orphan_dies_when_parent_killed(worker_py_exec, tmp_path):
    """親プロセス経由で B を起動し、親を強制 kill → B が孤児化せず消えることを確認。

    親（launcher）は B_worker を Popen で起動し、その pid を出力してから
    自身は sleep する。この launcher を kill すると B の stdin が閉じ、
    stdin-EOF 自死で B が消える。
    """
    launcher = tmp_path / "launcher.py"
    launcher.write_text(
        "import subprocess, sys, time\n"
        f"p = subprocess.Popen([{worker_py_exec!r}, {str(WORKER_PY)!r}],\n"
        "    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)\n"
        "# hello を1行読んで、B が立ち上がったことを確認\n"
        "p.stdout.readline()\n"
        "print(p.pid, flush=True)\n"
        "time.sleep(60)\n"
    )

    parent = subprocess.Popen(
        [sys.executable, str(launcher)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        # B の pid を受け取る
        line = parent.stdout.readline().strip()
        assert line, "launcher が B の pid を出力しなかった"
        b_pid = int(line)

        # B が生きていることを確認
        assert _pid_alive(b_pid)

        # 親を強制 kill（孤児化の起点）
        parent.kill()
        parent.wait(timeout=5)

        # stdin-EOF 自死で B が消えるのを待つ
        deadline = time.time() + 8
        while time.time() < deadline:
            if not _pid_alive(b_pid):
                break
            time.sleep(0.1)
        assert not _pid_alive(b_pid), "親を kill しても B が孤児として残った"
    finally:
        if _alive(parent):
            parent.kill()
            parent.wait(timeout=5)


def _pid_alive(pid: int) -> bool:
    """pid が生存しているか（POSIX / Windows 両対応の簡易判定）。"""
    if sys.platform == "win32":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
        )
        return str(pid) in out.stdout
    else:
        import os

        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
