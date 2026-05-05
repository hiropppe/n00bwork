"""Section 3: Judge list parser.

「参照記号 / 審判 / 会場識別コード」の3列テーブルから審判情報を抽出。
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from jdsf.ids import judge_id
from jdsf.models import EventJudge, Judge
from jdsf.normalize import normalize_name, normalize_text


class JudgeParseError(ValueError):
    pass


def parse_judges(soup: BeautifulSoup, *, event_id: str) -> tuple[list[Judge], list[EventJudge]]:
    table = _find_judges_table(soup)

    judges: list[Judge] = []
    event_judges: list[EventJudge] = []
    seen_refs: set[str] = set()

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 3:
            continue
        ref_raw, name_raw, venue_raw = (c.get_text("", strip=True) for c in cells)
        ref = normalize_text(ref_raw)
        name = name_raw.strip()
        venue = normalize_text(venue_raw)

        if not ref or ref == "参照記号":
            continue
        if ref in seen_refs:
            raise JudgeParseError(f"duplicate ref symbol: {ref!r}")
        if not name:
            continue

        name_normalized = normalize_name(name)
        jid = judge_id(name_normalized)

        judges.append(Judge(judge_id=jid, name=name, name_normalized=name_normalized))
        event_judges.append(
            EventJudge(
                event_id=event_id,
                ref_symbol=ref,
                judge_id=jid,
                venue_code=venue or None,
            )
        )
        seen_refs.add(ref)

    if not judges:
        raise JudgeParseError("no judges parsed")
    return judges, event_judges


def _find_judges_table(soup: BeautifulSoup):
    """「参照記号」を見出しに持つテーブルを探す。"""
    for td in soup.find_all("td"):
        if normalize_text(td.get_text(" ", strip=True)) == "参照記号":
            table = td.find_parent("table")
            if table is not None:
                return table
    raise JudgeParseError("judges table (参照記号 列) not found")
