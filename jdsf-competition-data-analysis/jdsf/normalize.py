"""Text normalization utilities for JDSF data."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")

# 種目コードの対応表。HTML 表記の揺れを単一文字に正規化する。
# 不明なものは UnknownDanceCode を投げる（fail-fast）。
_DANCE_CODE_TABLE: dict[str, str] = {
    "W": "W", "Wz": "W", "Waltz": "W",
    "T": "T", "Tg": "T", "Tango": "T",
    "V": "V", "VW": "V", "V.W": "V", "V.Waltz": "V", "V. Waltz": "V", "VWaltz": "V",
    "F": "F", "Sf": "F", "Slowfox": "F", "Slow Foxtrot": "F",
    "Q": "Q", "Qu": "Q", "Quickstep": "Q",
    "S": "S", "Sa": "S", "Samba": "S",
    "C": "C", "CC": "C", "ChaCha": "C", "Cha-cha-cha": "C", "Cha Cha Cha": "C",
    "R": "R", "Ru": "R", "Rumba": "R",
    "P": "P", "PD": "P", "PasoDoble": "P", "Paso Doble": "P", "Paso": "P",
    "J": "J", "Jv": "J", "Jive": "J",
}


class UnknownDanceCode(ValueError):
    """正規化できない種目表記が見つかったときに送出される。"""


def normalize_text(s: str) -> str:
    """NFKC 正規化、連続空白を1つに、両端トリム。"""
    s = unicodedata.normalize("NFKC", s)
    s = _WHITESPACE_RE.sub(" ", s).strip()
    return s


def normalize_name(s: str) -> str:
    """人名・所属名等の正規化。現在は normalize_text と同じ挙動。"""
    return normalize_text(s)


def normalize_dance_code(s: str) -> str:
    """種目表記を単一文字コードに正規化。未知なら UnknownDanceCode。"""
    s = unicodedata.normalize("NFKC", s).strip()
    # 括弧付き表記 '(V)' → 'V'
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    if s in _DANCE_CODE_TABLE:
        return _DANCE_CODE_TABLE[s]
    raise UnknownDanceCode(f"unknown dance code: {s!r}")
