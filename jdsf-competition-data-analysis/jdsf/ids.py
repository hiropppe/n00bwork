"""Deterministic ID generation for JDSF entities.

ID は SHA256 の上位 8 バイトを 63 ビットに丸めた正の BIGINT を採用する。
入力が同じであれば同じ ID になり、異なる入力は事実上衝突しない（64bit 空間）。
"""

from __future__ import annotations

import hashlib

_BIGINT_MASK = 0x7FFFFFFFFFFFFFFF  # 63ビット（DuckDB BIGINT の正値範囲）


def _hash_to_bigint(*parts: str) -> int:
    """文字列群を結合し、SHA256 上位8バイトの正値 BIGINT を返す。"""
    h = hashlib.sha256("|".join(parts).encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big") & _BIGINT_MASK


def person_id(name_normalized: str) -> int:
    return _hash_to_bigint("person", name_normalized)


def judge_id(name_normalized: str) -> int:
    return _hash_to_bigint("judge", name_normalized)


def couple_id(leader_id: int, partner_id: int) -> int:
    return _hash_to_bigint("couple", str(leader_id), str(partner_id))


def round_id(event_id: str, round_kind: str, round_seq: int) -> int:
    return _hash_to_bigint("round", event_id, round_kind, str(round_seq))
