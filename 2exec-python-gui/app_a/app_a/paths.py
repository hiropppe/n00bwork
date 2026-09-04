"""frozen / dev の実行ファイル・パス解決。

frozen（PyInstaller）では A.exe の隣（macOS は .app バンドル内）の b_worker を、
dev では subsystem_b/worker.py を B の venv の python で起動する。
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def worker_executable() -> Path:
    """B_worker の実行ファイル（frozen）または worker.py（dev）のパスを返す。

    frozen 時: A 実行ファイルの隣にある b_worker（Windows は b_worker.exe）。
        - Windows/Linux: <A のあるディレクトリ>/b_worker[.exe]
        - macOS .app: A は Contents/MacOS/ にいる。b_worker は Contents/Resources/
          に埋め込む方針なので、そちらを優先的に探す。
    dev 時: リポジトリ内の subsystem_b/worker.py。
    """
    if is_frozen():
        base = Path(sys.executable).parent
        name = "b_worker.exe" if sys.platform == "win32" else "b_worker"

        if sys.platform == "darwin":
            # .app/Contents/MacOS/A  → Resources に埋め込んだ b_worker を探す
            resources = base.parent / "Resources"
            candidate = resources / name
            if candidate.exists():
                return candidate
        # Windows / Linux、または macOS で MacOS 直下に置いた場合
        return base / name

    # dev: subsystem_b/worker.py（このファイルは app_a/app_a/paths.py）
    return Path(__file__).resolve().parents[2] / "subsystem_b" / "worker.py"


def dev_worker_python() -> Path | None:
    """dev 実行時に worker.py を起動する Python インタプリタを返す。

    B 専用 venv（subsystem_b/.venv）があればそれを使う。無ければ None を返し、
    呼び出し側で現在の python（sys.executable）にフォールバックする。
    ただし A の venv には numpy が無いので、B の venv があることが望ましい。
    """
    repo_root = Path(__file__).resolve().parents[2]
    venv = repo_root / "subsystem_b" / ".venv"
    if sys.platform == "win32":
        py = venv / "Scripts" / "python.exe"
    else:
        py = venv / "bin" / "python"
    return py if py.exists() else None
