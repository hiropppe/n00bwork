"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from jdsf.fetch import decode_local_html
from jdsf.parse.document import parse_document

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE_R260416_03 = FIXTURE_DIR / "R260416_03.html"
FIXTURE_R260416_03_URL = "https://kyougi.jdsf.or.jp/2026/260416/R260416_03.html"


@pytest.fixture(scope="session")
def fixture_html() -> str:
    """ジュニア スタンダード（260416_03）のローカル fixture を CP932 デコードして返す。"""
    if not FIXTURE_R260416_03.exists():
        pytest.skip(f"fixture not found: {FIXTURE_R260416_03}")
    return decode_local_html(FIXTURE_R260416_03)


@pytest.fixture(scope="session")
def fixture_soup(fixture_html: str):
    return parse_document(fixture_html)


@pytest.fixture(scope="session")
def fixture_url() -> str:
    return FIXTURE_R260416_03_URL
