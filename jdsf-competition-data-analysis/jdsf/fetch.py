"""HTTP fetch + CP932 decode for JDSF pages.

JDSF サーバは Shift-JIS（実態は CP932）で配信する。`SHIFT_JIS` だと Windows 拡張文字で
不正バイトとして失敗するため、必ず `cp932` を使う。

raw バイト列はそのままローカルに保存し、後で再パース可能にする。
"""

from __future__ import annotations

import hashlib
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

DEFAULT_TIMEOUT_SEC = 30
DEFAULT_USER_AGENT = "jdsf-competition-data-analysis/0.1 (+research)"


@dataclass(frozen=True, slots=True)
class FetchResult:
    url: str
    html: str
    raw_bytes: bytes
    raw_path: Path
    encoding: str
    sha256: str
    fetched_at: str  # ISO 8601 UTC


def fetch(
    url: str,
    raw_dir: Path,
    *,
    timeout: float = DEFAULT_TIMEOUT_SEC,
    user_agent: str = DEFAULT_USER_AGENT,
) -> FetchResult:
    """指定 URL を取得し、CP932 デコード文字列とローカル保存パス等を返す。

    raw_dir 配下に URL のパス構造を再現して .html を保存する。
    例: https://kyougi.jdsf.or.jp/2026/260416/R260416_03.html
        → raw_dir/kyougi.jdsf.or.jp/2026/260416/R260416_03.html
    """
    headers = {"User-Agent": user_agent}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()

    raw_bytes = resp.content
    html = raw_bytes.decode("cp932")

    sha = hashlib.sha256(raw_bytes).hexdigest()
    fetched_at = datetime.now(timezone.utc).isoformat()

    parsed = urllib.parse.urlparse(url)
    rel_path = (parsed.netloc + parsed.path).lstrip("/")
    out_path = raw_dir / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(raw_bytes)

    return FetchResult(
        url=url,
        html=html,
        raw_bytes=raw_bytes,
        raw_path=out_path,
        encoding="cp932",
        sha256=sha,
        fetched_at=fetched_at,
    )


def decode_local_html(path: Path) -> str:
    """ローカル保存済みの HTML（CP932）を UTF-8 文字列に。"""
    return path.read_bytes().decode("cp932")
