"""Section 7: Per-dance final results parser.

各種目（Waltz/Tango/V.Waltz/Slowfox/Quickstep 等）ごとのテーブルから
- 審判別の順位マーク（judge_marks, mark_type='placement'）
- 判定方式（多数決 / 上位加算 / 等）を抽出。

判定方式は round_dance_results.decision_method に反映するため、(bib, dance_code) -> str
のマップとして返す。
"""

from __future__ import annotations

from collections.abc import Iterable

from bs4 import BeautifulSoup

from jdsf.models import EventJudge, JudgeMark, Round
from jdsf.normalize import UnknownDanceCode, normalize_dance_code, normalize_text


class PerDanceParseError(ValueError):
    pass


def parse_per_dance(
    soup: BeautifulSoup,
    *,
    finals_round: Round,
    event_judges: Iterable[EventJudge],
) -> tuple[list[JudgeMark], dict[tuple[int, str], str | None]]:
    """Section 7 全体（複数種目）をパース。

    Returns:
        marks: 全種目分の JudgeMark（mark_type='placement'）
        decisions: {(bib, dance_code) -> '多数決' / '上位加算' / None}
    """
    valid_refs = {ej.ref_symbol for ej in event_judges}
    if not valid_refs:
        raise PerDanceParseError("event_judges が空のため Section 7 のパース不可")

    marks: list[JudgeMark] = []
    decisions: dict[tuple[int, str], str | None] = {}
    seen_codes: set[str] = set()

    for elem in soup.find_all(["b", "td"]):
        text = normalize_text(elem.get_text(" "))
        if "●" not in text:
            continue
        # マーカー以降の語が種目名であるかチェック
        after = text.split("●", 1)[1].strip()
        try:
            dance_code = normalize_dance_code(after)
        except UnknownDanceCode:
            continue
        if dance_code in seen_codes:
            continue

        current_table = elem.find_parent("table")
        if current_table is None:
            continue
        next_table = current_table.find_next("table")
        if next_table is None:
            continue

        added = _parse_one_dance_table(
            next_table,
            finals_round=finals_round,
            dance_code=dance_code,
            valid_refs=valid_refs,
            marks=marks,
            decisions=decisions,
        )
        if added:
            seen_codes.add(dance_code)

    if not marks:
        raise PerDanceParseError("Section 7 のマークが0件")
    return marks, decisions


def _parse_one_dance_table(
    table,
    *,
    finals_round: Round,
    dance_code: str,
    valid_refs: set[str],
    marks: list[JudgeMark],
    decisions: dict[tuple[int, str], str | None],
) -> bool:
    rows = list(table.find_all("tr"))
    header_idx = _find_header_row_idx(rows)
    if header_idx is None:
        return False
    header_cells = rows[header_idx].find_all("td")
    column_map = _map_per_dance_columns(header_cells, valid_refs)
    if not column_map["judges"]:
        return False

    added = False
    for row in rows[header_idx + 1 :]:
        cells = row.find_all("td")
        max_required = max(
            column_map["bib"],
            column_map.get("decision") or 0,
            *(i for _ref, i in column_map["judges"]),
        )
        if len(cells) <= max_required:
            continue
        bib_text = _cell_text(cells[column_map["bib"]])
        if not bib_text.isdigit():
            continue
        bib = int(bib_text)

        for ref, col_i in column_map["judges"]:
            text = _cell_text(cells[col_i])
            placement = _parse_int_or_none(text)
            if placement is None:
                continue
            marks.append(
                JudgeMark(
                    event_id=finals_round.event_id,
                    round_id=finals_round.round_id,
                    bib_number=bib,
                    dance_code=dance_code,
                    judge_ref=ref,
                    mark_type="placement",
                    recalled=None,
                    placement=placement,
                )
            )
            added = True

        if column_map.get("decision") is not None:
            decision_text = _cell_text(cells[column_map["decision"]])
            decisions[(bib, dance_code)] = decision_text or None
    return added


def _find_header_row_idx(rows) -> int | None:
    for i, row in enumerate(rows):
        for cell in row.find_all("td"):
            if normalize_text(cell.get_text(" ")) == "背番号":
                return i
    return None


def _map_per_dance_columns(header_cells, valid_refs: set[str]) -> dict:
    bib_idx: int | None = None
    rank_idx: int | None = None
    decision_idx: int | None = None
    judges: list[tuple[str, int]] = []

    for i, cell in enumerate(header_cells):
        text = normalize_text(cell.get_text(" "))
        if text == "背番号":
            bib_idx = i
            continue
        if text == "順位":
            rank_idx = i
            continue
        if text == "判定":
            decision_idx = i
            continue
        if text in valid_refs:
            judges.append((text, i))

    if bib_idx is None:
        raise PerDanceParseError("'背番号' 列が見つからない")

    return {
        "bib": bib_idx,
        "judges": judges,
        "rank": rank_idx,
        "decision": decision_idx,
    }


def _cell_text(td) -> str:
    raw = td.get_text(" ", strip=True)
    if raw.replace("　", "").strip() == "":
        return ""
    # 末尾の全角空白も除去
    return raw.strip("　 ")


def _parse_int_or_none(s: str) -> int | None:
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None
