"""Top-level document parsing utilities."""

from __future__ import annotations

import re
import urllib.parse

from bs4 import BeautifulSoup


def parse_document(html: str) -> BeautifulSoup:
    """HTML 文字列を BeautifulSoup（lxml バックエンド）でパース。"""
    return BeautifulSoup(html, "lxml")


_SEQ_FROM_URL_RE = re.compile(r"R\d+_(\d+)\.html?$", re.IGNORECASE)


def extract_seq_from_url(url: str) -> int:
    """URL の末尾 'R260416_03.html' 等から seq（種別ファイル番号）を抽出。"""
    path = urllib.parse.urlparse(url).path
    m = _SEQ_FROM_URL_RE.search(path)
    if not m:
        raise ValueError(f"cannot extract seq from URL path: {path!r}")
    return int(m.group(1))


def make_event_id(competition_id: str, seq: int) -> str:
    """event_id = '{competition_id}_{seq:02d}'."""
    return f"{competition_id}_{seq:02d}"
