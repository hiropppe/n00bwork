"""Section 8: Round-by-round detail parser.

Section 8 はラウンド見出し（■決勝 / ■準決勝 / ■１次予選 ...）と続く詳細表で構成される。

提供する関数：
- `extract_round_structure`: ラウンド見出しを拾って Round[] を構築（round_seq を割り当て）
- `parse_round_details`: 各ラウンドのテーブルを読み、judge_marks と round_dance_results を返す

決勝の judge_marks（placement）は per_dance.parse_per_dance で取得済みのため、本モジュールでは
Section 8 の決勝行は**スキップ**する（重複防止）。Section 8 から取るのは予選・準決勝のリコール情報のみ。
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from bs4 import BeautifulSoup

from jdsf.ids import round_id
from jdsf.models import EventJudge, JudgeMark, Round, RoundDanceResult
from jdsf.normalize import UnknownDanceCode, normalize_dance_code, normalize_text

_PRELIM_RE = re.compile(r"^(\d+)次予選$")
_PRELIM_CELL_RE = re.compile(r"^(\d+)予$")
# 注: '決勝' が '準決勝' にも一致するため、長いキーワードから先に判定する
_ROUND_HEADERS = ("準決勝", "決勝")


class RoundsParseError(ValueError):
    pass


# ---------------------------------------------------------------------------
# ラウンド構造抽出（Step 5 で実装済）
# ---------------------------------------------------------------------------


def extract_round_structure(soup: BeautifulSoup, *, event_id: str) -> list[Round]:
    found_kinds: list[tuple[str, str, int | None]] = []
    seen: set[str] = set()

    for td in soup.find_all("td"):
        b = td.find("b")
        if b is None:
            continue
        text = normalize_text(b.get_text(" "))
        if "■" not in text:
            continue
        label = _extract_round_label(text)
        if label is None or label in seen:
            continue
        seen.add(label)
        kind, prelim_n = _classify_round_label(label)
        if kind is None:
            continue
        found_kinds.append((kind, label, prelim_n))

    if not found_kinds:
        raise RoundsParseError("no round section headers found")

    def _sort_key(item: tuple[str, str, int | None]) -> tuple[int, int]:
        kind, _label, n = item
        kind_order = {"prelim": 0, "semifinal": 1, "final": 2}[kind]
        return (kind_order, n or 0)

    found_kinds.sort(key=_sort_key)

    rounds: list[Round] = []
    for seq, (kind, label, _n) in enumerate(found_kinds, start=1):
        rid = round_id(event_id, kind, seq)
        rounds.append(
            Round(
                round_id=rid,
                event_id=event_id,
                round_kind=kind,
                round_seq=seq,
                label_jp=label,
                couples_in=None,
                couples_out=None,
                recall_threshold=None,
            )
        )
    return rounds


# ---------------------------------------------------------------------------
# ラウンド別詳細パース（Step 7）
# ---------------------------------------------------------------------------


def parse_round_details(
    soup: BeautifulSoup,
    *,
    rounds: Iterable[Round],
    event_judges: Iterable[EventJudge],
) -> tuple[list[JudgeMark], list[RoundDanceResult]]:
    """Section 8 の決勝/準決勝/予選テーブルから judge_marks と round_dance_results を抽出。

    決勝行は per_dance で重複処理されるため本関数では skip。
    予選・準決勝行から：
      - judge_marks (mark_type='recall', recalled=True/False)
      - round_dance_results (recall_total)
    """
    refs = sorted({ej.ref_symbol for ej in event_judges})
    if not refs:
        raise RoundsParseError("event_judges が空のため Section 8 のパース不可")
    n_judges = len(refs)

    rounds_list = list(rounds)
    if not rounds_list:
        return [], []

    marks: list[JudgeMark] = []
    rdrs: list[RoundDanceResult] = []

    section_tables = _find_section_tables(soup)
    for label_jp, table in section_tables:
        _parse_one_section_table(
            table,
            rounds=rounds_list,
            refs=refs,
            n_judges=n_judges,
            marks=marks,
            rdrs=rdrs,
        )

    return marks, rdrs


def _find_section_tables(soup: BeautifulSoup) -> list[tuple[str, object]]:
    results: list[tuple[str, object]] = []
    seen_labels: set[str] = set()
    for td in soup.find_all("td"):
        b = td.find("b")
        if b is None:
            continue
        text = normalize_text(b.get_text(" "))
        if "■" not in text:
            continue
        label = _extract_round_label(text)
        if label is None or label in seen_labels:
            continue
        kind, _n = _classify_round_label(label)
        if kind is None:
            continue
        seen_labels.add(label)
        current_table = b.find_parent("table")
        if current_table is None:
            continue
        next_table = current_table.find_next("table")
        if next_table is not None:
            results.append((label, next_table))
    return results


def _parse_one_section_table(
    table,
    *,
    rounds: list[Round],
    refs: list[str],
    n_judges: int,
    marks: list[JudgeMark],
    rdrs: list[RoundDanceResult],
) -> None:
    rows = list(table.find_all("tr"))
    if not rows:
        return
    dance_codes = _extract_dance_order_from_header(rows)
    if not dance_codes:
        return

    current_bib: int | None = None
    for tr in rows:
        cells = tr.find_all("td")
        if len(cells) == 2:
            # 組の開始行 (順位, 背番号)
            bib_text = _cell_text(cells[1])
            current_bib = int(bib_text) if bib_text.isdigit() else None
            continue

        # ラウンド情報行: ラウンド名 + dance_codes 数 + 合計列
        expected_cols = 1 + len(dance_codes) + 1
        if len(cells) != expected_cols or current_bib is None:
            continue

        round_label = _cell_text(cells[0])
        target_round = _round_from_cell_label(round_label, rounds)
        if target_round is None:
            continue
        # 決勝行は per_dance 経由で取得済みのためスキップ
        if target_round.round_kind == "final":
            continue

        for col_i, dance_code in enumerate(dance_codes, start=1):
            payload_cell = cells[col_i]
            payload = _payload_text(payload_cell)
            if not payload:
                continue
            head, tail = _split_payload(payload, n_judges)
            if not head or len(head) < n_judges:
                continue

            for ref, ch in zip(refs, head[:n_judges], strict=True):
                marks.append(
                    JudgeMark(
                        event_id=target_round.event_id,
                        round_id=target_round.round_id,
                        bib_number=current_bib,
                        dance_code=dance_code,
                        judge_ref=ref,
                        mark_type="recall",
                        recalled=(ch == "O"),
                        placement=None,
                    )
                )

            recall_total = _parse_int_or_none(tail)
            rdrs.append(
                RoundDanceResult(
                    event_id=target_round.event_id,
                    round_id=target_round.round_id,
                    bib_number=current_bib,
                    dance_code=dance_code,
                    recall_total=recall_total,
                    placement_score=None,
                    dance_rank=None,
                    decision_method=None,
                )
            )


def _extract_dance_order_from_header(rows) -> list[str]:
    """ヘッダ TR から種目コード順を取得（Waltz/Tango/...）。

    Section 8 のヘッダは複数 TR にまたがる（順位/背番号/ラウンド + 種目 + 合計、
    続いて 'ABCDEFG +' 行）。種目を含む行を探して採用。
    """
    for row in rows[:6]:  # 上位の数行だけ走査
        codes: list[str] = []
        for cell in row.find_all("td"):
            text = normalize_text(cell.get_text(" "))
            try:
                codes.append(normalize_dance_code(text))
            except UnknownDanceCode:
                continue
        if len(codes) >= 3:  # 種目数 3 以上ならヘッダ行とみなす
            return codes
    return []


def _payload_text(td) -> str:
    """ペイロードセルから 'OO-OOO- 5' のような文字列を取り出す（連続空白を圧縮）。"""
    raw = td.get_text(" ", strip=True)
    parts = raw.split()
    return " ".join(parts)


def _split_payload(payload: str, n: int) -> tuple[str, str]:
    s = payload.strip()
    if len(s) >= n:
        head = s[:n]
        tail = s[n:].strip()
        return head, tail
    return "", s


def _round_from_cell_label(label: str, rounds: list[Round]) -> Round | None:
    label_norm = normalize_text(label)
    if label_norm == "決勝":
        return next((r for r in rounds if r.round_kind == "final"), None)
    if label_norm == "準決":
        return next((r for r in rounds if r.round_kind == "semifinal"), None)
    m = _PRELIM_CELL_RE.match(label_norm)
    if m:
        n = int(m.group(1))
        prelims = sorted(
            [r for r in rounds if r.round_kind == "prelim"], key=lambda r: r.round_seq
        )
        if 1 <= n <= len(prelims):
            return prelims[n - 1]
    return None


def _cell_text(td) -> str:
    raw = td.get_text(" ", strip=True)
    if raw.replace("　", "").strip() == "":
        return ""
    return raw.strip("　 ")


def _parse_int_or_none(s: str) -> int | None:
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 内部ヘルパ（ラウンド構造抽出側）
# ---------------------------------------------------------------------------


def _extract_round_label(header_text: str) -> str | None:
    if "■" not in header_text:
        return None
    after = header_text.split("■", 1)[1]
    after = normalize_text(after)
    for kw in _ROUND_HEADERS:
        if after.endswith(kw):
            return kw
    if _PRELIM_RE.search(after):
        m = _PRELIM_RE.search(after)
        assert m is not None
        return m.group(0)
    return None


def _classify_round_label(label: str) -> tuple[str | None, int | None]:
    if label == "決勝":
        return ("final", None)
    if label == "準決勝":
        return ("semifinal", None)
    m = _PRELIM_RE.match(label)
    if m:
        return ("prelim", int(m.group(1)))
    return (None, None)
