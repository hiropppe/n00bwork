"""Sections 4-6: Final overall results (規定1-9 / 10 / 11).

Section 4 「規定1-9」: 決勝総合の種目別順位 + 合計 + 総合順位
Section 5 「規定10」: 多数決・上位加算によるタイブレーク
Section 6 「規定11」: 再スケーティング

総合タイブレーク（規定10/11）は dance_code='_TOTAL_' センチネルで保存。
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from jdsf.models import Round, RoundDanceResult, RoundTotal, SkatingTiebreak
from jdsf.normalize import UnknownDanceCode, normalize_dance_code, normalize_text

TOTAL_DANCE_SENTINEL = "_TOTAL_"


class OverallParseError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Section 4: 規定1-9（決勝総合）
# ---------------------------------------------------------------------------


def parse_overall_finals(
    soup: BeautifulSoup, *, finals_round: Round
) -> tuple[list[RoundDanceResult], list[RoundTotal]]:
    table = _find_table_after_marker(soup, "規定1-9")
    if table is None:
        raise OverallParseError("規定1-9 テーブルが見つからない")

    rows = list(table.find_all("tr"))
    header_idx = _find_header_row_idx(rows)
    if header_idx is None:
        raise OverallParseError("規定1-9: ヘッダ行（'背番号' 列）が見つからない")

    header_cells = rows[header_idx].find_all("td")
    column_map = _map_overall_columns(header_cells)

    round_dance_results: list[RoundDanceResult] = []
    round_totals: list[RoundTotal] = []
    seen_bibs: set[int] = set()

    for row in rows[header_idx + 1 :]:
        cells = row.find_all("td")
        if len(cells) <= column_map["rank"]:
            continue
        bib_text = _cell_text(cells[column_map["bib"]])
        if not bib_text.isdigit():
            continue
        bib = int(bib_text)
        if bib in seen_bibs:
            raise OverallParseError(f"規定1-9: 重複した背番号 {bib}")
        seen_bibs.add(bib)

        for col_i, dance_code in column_map["dances"]:
            text = _cell_text(cells[col_i])
            if not text:
                continue
            try:
                rank = int(text)
            except ValueError:
                continue
            round_dance_results.append(
                RoundDanceResult(
                    event_id=finals_round.event_id,
                    round_id=finals_round.round_id,
                    bib_number=bib,
                    dance_code=dance_code,
                    recall_total=None,
                    placement_score=None,
                    dance_rank=rank,
                    decision_method=None,
                )
            )

        total_text = _cell_text(cells[column_map["total"]])
        rank_text = _cell_text(cells[column_map["rank"]])
        total_score = _parse_float_or_none(total_text)
        round_rank = _parse_int_or_none(rank_text)
        round_totals.append(
            RoundTotal(
                event_id=finals_round.event_id,
                round_id=finals_round.round_id,
                bib_number=bib,
                total_score=total_score,
                round_rank=round_rank,
            )
        )

    if not round_totals:
        raise OverallParseError("規定1-9: データ行が0件")

    return round_dance_results, round_totals


# ---------------------------------------------------------------------------
# Section 5/6: 規定10 / 規定11（タイブレーク）
# ---------------------------------------------------------------------------


def parse_skating_tiebreak(
    soup: BeautifulSoup, *, finals_round: Round, rule_no: int
) -> list[SkatingTiebreak]:
    """規定10 または規定11 のタイブレーク行をパース。

    rule_no=10 / 11 を指定。HTML 上の見出しは「規定10」「規定11」（NFKC 後）。
    """
    marker = f"規定{rule_no}"
    table = _find_table_after_marker(soup, marker)
    if table is None:
        raise OverallParseError(f"{marker} テーブルが見つからない")

    rows = list(table.find_all("tr"))
    header_idx = _find_header_row_idx(rows)
    if header_idx is None:
        raise OverallParseError(f"{marker}: ヘッダ行が見つからない")

    tiebreaks: list[SkatingTiebreak] = []
    seen_bibs: set[int] = set()

    for row in rows[header_idx + 1 :]:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        bib_text = _cell_text(cells[0])
        if not bib_text.isdigit():
            continue
        bib = int(bib_text)
        if bib in seen_bibs:
            continue
        seen_bibs.add(bib)

        rank_text = _cell_text(cells[-1])
        final_rank = _parse_int_or_none(rank_text)

        middle = cells[1:-1]
        cumulative: tuple[int, ...] | None
        not_applicable: bool

        if len(middle) == 1:
            # COLSPAN=9 で「規定N適用外」ケース
            text = _cell_text(middle[0])
            cumulative = None
            not_applicable = "適用外" in text
        elif len(middle) == 9:
            values: list[int] = []
            for c in middle:
                t = _cell_text(c)
                try:
                    values.append(int(t))
                except ValueError:
                    values.append(0)
            cumulative = tuple(values)
            not_applicable = False
        else:
            raise OverallParseError(
                f"{marker}: 想定外の中間セル数 {len(middle)} (bib={bib})"
            )

        tiebreaks.append(
            SkatingTiebreak(
                event_id=finals_round.event_id,
                round_id=finals_round.round_id,
                bib_number=bib,
                dance_code=TOTAL_DANCE_SENTINEL,
                rule_no=rule_no,
                cumulative=cumulative,
                final_rank=final_rank,
                not_applicable=not_applicable,
            )
        )

    if not tiebreaks:
        raise OverallParseError(f"{marker}: データ行が0件")
    return tiebreaks


# ---------------------------------------------------------------------------
# 共通ヘルパ
# ---------------------------------------------------------------------------


def _find_table_after_marker(soup: BeautifulSoup, marker: str):
    """マーカー文字列を含むテキスト要素の後の最初の <table> を取得。"""
    for elem in soup.find_all(["b", "td"]):
        text = normalize_text(elem.get_text(" "))
        if marker in text:
            # 直近の祖先 table を起点にして、その次の table を探す
            current_table = elem.find_parent("table")
            if current_table is None:
                continue
            next_table = current_table.find_next("table")
            if next_table is not None:
                return next_table
    return None


def _find_header_row_idx(rows) -> int | None:
    for i, row in enumerate(rows):
        cells = row.find_all("td")
        for cell in cells:
            if normalize_text(cell.get_text(" ")) == "背番号":
                return i
    return None


def _map_overall_columns(header_cells) -> dict:
    """規定1-9 ヘッダ TR のセル並びから列マッピングを作る。

    並びは [背番号, Wz, Tg, ..., Jv, 合計, 総合順位, 備考] という構造。
    種目セルは normalize_dance_code に通せるテキストを持つ。
    """
    bib_idx: int | None = None
    total_idx: int | None = None
    rank_idx: int | None = None
    dance_columns: list[tuple[int, str]] = []

    for i, cell in enumerate(header_cells):
        text = normalize_text(cell.get_text(" "))
        if text == "背番号":
            bib_idx = i
            continue
        if text == "合計":
            total_idx = i
            continue
        if text == "総合順位":
            rank_idx = i
            continue
        if text in ("備考", ""):
            continue
        try:
            code = normalize_dance_code(text)
        except UnknownDanceCode:
            continue
        dance_columns.append((i, code))

    if bib_idx is None or total_idx is None or rank_idx is None:
        raise OverallParseError(
            f"規定1-9 ヘッダの解釈に失敗 (bib={bib_idx}, total={total_idx}, rank={rank_idx})"
        )

    return {
        "bib": bib_idx,
        "total": total_idx,
        "rank": rank_idx,
        "dances": dance_columns,
    }


def _cell_text(td) -> str:
    raw = td.get_text(" ", strip=True)
    if raw.replace("　", "").strip() == "":
        return ""
    return raw


def _parse_int_or_none(s: str) -> int | None:
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _parse_float_or_none(s: str) -> float | None:
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None
