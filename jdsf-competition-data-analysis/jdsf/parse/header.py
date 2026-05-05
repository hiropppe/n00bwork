"""Section 1: Competition header parser.

ヘッダのテーブルから (Competition, Event) を取り出す。

ページの該当部分は「許可番号」「大会名称」「開催会場」「開催日付」
「種別ｺｰﾄﾞ」「競技名称」「競技種目」「参加組数」のラベル行で構成される。
"""

from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup, Tag

from jdsf.models import Competition, Event
from jdsf.normalize import normalize_dance_code, normalize_text
from jdsf.parse.document import extract_seq_from_url, make_event_id

_HEADER_LABELS = (
    "許可番号",
    "大会名称",
    "開催会場",
    "開催日付",
    "種別コード",  # NFKC 後のキー名
    "競技名称",
    "競技種目",
    "参加組数",
)

_DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
_PARTICIPANT_COUNT_RE = re.compile(r"(\d+)\s*組")
_JUDGE_COUNT_RE = re.compile(r"審判員数\s*[＝=]\s*(\d+)")


class HeaderParseError(ValueError):
    """ヘッダパースに失敗した場合に送出。"""


def parse_header(soup: BeautifulSoup, *, source_url: str) -> tuple[Competition, Event]:
    label_map = _extract_label_value_map(soup)

    missing = [lab for lab in _HEADER_LABELS if lab not in label_map]
    if missing:
        raise HeaderParseError(f"missing header labels: {missing}")

    competition_id = normalize_text(label_map["許可番号"])
    name = normalize_text(label_map["大会名称"])
    venue = normalize_text(label_map["開催会場"]) or None
    held_on = _parse_japanese_date(label_map["開催日付"])

    category_code = normalize_text(label_map["種別コード"])
    category_name = normalize_text(label_map["競技名称"])
    dances_raw = label_map["競技種目"]
    dances = tuple(
        normalize_dance_code(line.strip())
        for line in dances_raw.splitlines()
        if line.strip()
    )

    entries, couples_started = _parse_participant_counts(label_map["参加組数"])
    judge_count = _extract_judge_count(soup)

    seq = extract_seq_from_url(source_url)
    event_id = make_event_id(competition_id, seq)

    competition = Competition(
        competition_id=competition_id,
        name=name,
        venue=venue,
        held_on=held_on,
    )
    event = Event(
        event_id=event_id,
        competition_id=competition_id,
        seq=seq,
        category_code=category_code,
        category_name=category_name,
        discipline=None,  # 種別コードからの推定は別フェーズ
        age_group=None,
        dances=dances,
        entries=entries,
        couples_started=couples_started,
        judge_count=judge_count,
        source_url=source_url,
    )
    return competition, event


def _extract_label_value_map(soup: BeautifulSoup) -> dict[str, str]:
    """ヘッダ TR 群から「ラベル → 値」のマップを作る。

    ラベルセルは <B> タグ内に上記ラベル文字列を含む TD として現れ、
    同じ TR の最後の TD が値。
    """
    label_set = set(_HEADER_LABELS)
    result: dict[str, str] = {}

    for b_tag in soup.find_all("b"):
        label_raw = b_tag.get_text(strip=True)
        if not label_raw:
            continue
        label_norm = normalize_text(label_raw)
        if label_norm not in label_set or label_norm in result:
            continue
        tr = b_tag.find_parent("tr")
        if tr is None:
            continue
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 2:
            continue
        # 値は最後の TD（ラベルと値の間にスペーサ TD がある構造のため）
        value_cell: Tag = tds[-1]
        # 改行を保つために get_text("\n", strip=False) で取り、後で strip
        value = value_cell.get_text("\n", strip=False).strip("　 \n\r\t")
        result[label_norm] = value

    return result


def _parse_japanese_date(s: str) -> date:
    s = normalize_text(s)
    m = _DATE_RE.search(s)
    if not m:
        raise HeaderParseError(f"cannot parse date: {s!r}")
    y, mo, d = (int(x) for x in m.groups())
    return date(y, mo, d)


def _parse_participant_counts(s: str) -> tuple[int | None, int | None]:
    """'15 組 /［ エントリー（申込）数 15 組 ］' のような文字列から組数を抽出。

    最初の数字を couples_started、2 つ目（あれば）を entries とみなす。
    """
    s = normalize_text(s)
    matches = _PARTICIPANT_COUNT_RE.findall(s)
    if not matches:
        return None, None
    couples_started = int(matches[0])
    entries = int(matches[1]) if len(matches) >= 2 else None
    return entries, couples_started


def _extract_judge_count(soup: BeautifulSoup) -> int | None:
    """文書全体から '審判員数 ＝ 7 名' 表記を探して整数値で返す。"""
    text = normalize_text(soup.get_text(" "))
    m = _JUDGE_COUNT_RE.search(text)
    if not m:
        return None
    return int(m.group(1))
