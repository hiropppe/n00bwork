"""テスト共通のフィクスチャ/ヘルパー。

worker.py を subprocess で起動して IPC する結合テスト用。B の venv
（subsystem_b/.venv）があればその python を使う（numpy が必要なため）。
無ければ現在の python にフォールバックする（numpy 未導入だと B が
import に失敗し、当該テストは skip される）。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PY = REPO_ROOT / "subsystem_b" / "worker.py"


def worker_python() -> str:
    """worker.py を起動する python 実行ファイルのパス。"""
    venv = REPO_ROOT / "subsystem_b" / ".venv"
    if sys.platform == "win32":
        py = venv / "Scripts" / "python.exe"
    else:
        py = venv / "bin" / "python"
    return str(py) if py.exists() else sys.executable


def _numpy_available(python: str) -> bool:
    try:
        subprocess.run(
            [python, "-c", "import numpy"],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def worker_py_exec() -> str:
    py = worker_python()
    if not _numpy_available(py):
        pytest.skip(
            "numpy が使える python が無いため worker 結合テストをスキップ "
            "（`cd subsystem_b && uv venv && uv pip install numpy` で用意）"
        )
    return py


class WorkerProcess:
    """worker.py の subprocess を1行送受信でラップするヘルパー。"""

    def __init__(self, python: str):
        self.proc = subprocess.Popen(
            [python, str(WORKER_PY)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # 行バッファ
        )

    def send(self, line: str) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def recv(self) -> str:
        assert self.proc.stdout is not None
        return self.proc.stdout.readline()

    def close_stdin(self) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.close()

    def __enter__(self) -> "WorkerProcess":
        return self

    def __exit__(self, *exc) -> None:
        try:
            if self.proc.poll() is None:
                self.proc.kill()
        finally:
            self.proc.wait(timeout=5)
