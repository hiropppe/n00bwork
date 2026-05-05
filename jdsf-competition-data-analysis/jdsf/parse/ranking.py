"""Section 2: Final ranking summary parser.

順位 / 背番号 / リーダー名 / パートナー名 / 所属 / 備考 の6列テーブルを読み取り、
Person / Couple / EventEntry を構築する。

順位ラベルは
  - 整数: 決勝進出（タイの場合は同じ値が複数行）
  - "１次", "２次": 各次予選で敗退（NFKC で "1次", "2次"）
  - "準決": 準決勝で敗退
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from jdsf.ids import couple_id, person_id
from jdsf.models import Couple, EventEntry, Person
from jdsf.normalize import normalize_name, normalize_text

_PRELIM_RE = re.compile(r"^(\d+)次$")


class RankingParseError(ValueError):
    pass


def parse_ranking(
    soup: BeautifulSoup, *, event_id: str
) -> tuple[list[Person], list[Couple], list[EventEntry]]:
    table = _find_ranking_table(soup)

    persons_by_id: dict[int, Person] = {}
    couples_by_id: dict[int, Couple] = {}
    entries: list[EventEntry] = []
    seen_bibs: set[int] = set()

    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) != 6:
            continue

        rank_raw = _cell_text(cells[0])
        bib_raw = _cell_text(cells[1])
        leader_raw = _cell_text(cells[2])
        partner_raw = _cell_text(cells[3])
        affiliation_raw = _cell_text(cells[4])
        note_raw = _cell_text(cells[5])

        # ヘッダ行・空セパレータをスキップ
        if rank_raw in ("順位", "") or bib_raw in ("背番号", ""):
            continue
        if not bib_raw.isdigit():
            continue

        rank_label = normalize_text(rank_raw)
        final_rank, eliminated_round = _interpret_rank(rank_label)

        bib = int(bib_raw)
        if bib in seen_bibs:
            raise RankingParseError(f"duplicate bib_number {bib} in ranking section")
        seen_bibs.add(bib)

        leader_name = leader_raw
        partner_name = partner_raw
        leader_norm = normalize_name(leader_name)
        partner_norm = normalize_name(partner_name)
        if not leader_norm or not partner_norm:
            raise RankingParseError(f"empty couple name in row bib={bib}")

        leader_pid = person_id(leader_norm)
        partner_pid = person_id(partner_norm)
        cid = couple_id(leader_pid, partner_pid)

        persons_by_id.setdefault(
            leader_pid,
            Person(person_id=leader_pid, name=leader_name, name_normalized=leader_norm),
        )
        persons_by_id.setdefault(
            partner_pid,
            Person(person_id=partner_pid, name=partner_name, name_normalized=partner_norm),
        )
        couples_by_id.setdefault(
            cid, Couple(couple_id=cid, leader_id=leader_pid, partner_id=partner_pid)
        )

        affiliation = normalize_text(affiliation_raw) or None
        note = normalize_text(note_raw) or None

        entries.append(
            EventEntry(
                event_id=event_id,
                bib_number=bib,
                couple_id=cid,
                affiliation=affiliation,
                final_rank_label=rank_label,
                final_rank=final_rank,
                eliminated_round=eliminated_round,
                note=note,
            )
        )

    if not entries:
        raise RankingParseError("no ranking rows parsed")

    return list(persons_by_id.values()), list(couples_by_id.values()), entries


def _cell_text(td) -> str:
    """セル内のテキストを取得（&nbsp; を空白扱い、両端トリム、全角空白除去）。"""
    raw = td.get_text(" ", strip=True)
    # 全角空白で囲まれた装飾セル（"　"のみ）は空文字に
    if raw.replace("　", "").strip() == "":
        return ""
    return raw


def _interpret_rank(label: str) -> tuple[int | None, str | None]:
    """順位ラベルから (final_rank, eliminated_round) を決める。"""
    if label.isdigit():
        return int(label), None
    m = _PRELIM_RE.match(label)
    if m:
        return None, f"{m.group(1)}次予選"
    if label in ("準決", "準決勝"):
        return None, "準決勝"
    raise RankingParseError(f"unknown rank label: {label!r}")


def _find_ranking_table(soup: BeautifulSoup):
    """ヘッダに「リーダー名」を含むテーブルを取得。"""
    for td in soup.find_all("td"):
        if normalize_text(td.get_text(" ", strip=True)) == "リーダー名":
            table = td.find_parent("table")
            if table is not None:
                return table
    raise RankingParseError("ranking table (リーダー名 列) not found")
