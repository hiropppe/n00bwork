"""Section parsers for JDSF result pages."""

from __future__ import annotations

from dataclasses import replace

from jdsf.models import ParsedPage, RawPage
from jdsf.parse.document import parse_document
from jdsf.parse.header import parse_header
from jdsf.parse.judges import parse_judges
from jdsf.parse.overall import parse_overall_finals, parse_skating_tiebreak
from jdsf.parse.per_dance import parse_per_dance
from jdsf.parse.ranking import parse_ranking
from jdsf.parse.rounds import extract_round_structure, parse_round_details


def parse_page(html: str, *, source_url: str, raw_page: RawPage | None = None) -> ParsedPage:
    """1ページの HTML を解析して ParsedPage を構築する。

    実装範囲：全 8 セクション（ヘッダ / 順位 / 審判 / 決勝総合 / 規定10 / 規定11 / 種目別決勝 / ラウンド別詳細）。
    """
    soup = parse_document(html)
    competition, event = parse_header(soup, source_url=source_url)
    judges, event_judges = parse_judges(soup, event_id=event.event_id)
    persons, couples, entries = parse_ranking(soup, event_id=event.event_id)

    rounds = extract_round_structure(soup, event_id=event.event_id)
    finals_round = next((r for r in rounds if r.round_kind == "final"), None)

    round_dance_results = []
    round_totals = []
    skating_tiebreaks = []
    marks = []

    if finals_round is not None:
        # Section 4: 決勝総合（規定1-9）
        round_dance_results, round_totals = parse_overall_finals(
            soup, finals_round=finals_round
        )
        # Section 5/6: 規定10/11
        skating_tiebreaks.extend(
            parse_skating_tiebreak(soup, finals_round=finals_round, rule_no=10)
        )
        skating_tiebreaks.extend(
            parse_skating_tiebreak(soup, finals_round=finals_round, rule_no=11)
        )
        # Section 7: 種目別決勝（judge_marks placement + decision_method）
        per_dance_marks, decisions = parse_per_dance(
            soup, finals_round=finals_round, event_judges=event_judges
        )
        marks.extend(per_dance_marks)
        round_dance_results = [
            replace(r, decision_method=decisions.get((r.bib_number, r.dance_code)))
            for r in round_dance_results
        ]

    # Section 8: ラウンド別詳細（予選・準決勝の judge_marks recall + recall_total）
    section8_marks, section8_rdrs = parse_round_details(
        soup, rounds=rounds, event_judges=event_judges
    )
    marks.extend(section8_marks)
    round_dance_results.extend(section8_rdrs)

    return ParsedPage(
        competition=competition,
        event=event,
        raw_page=raw_page,
        persons=persons,
        judges=judges,
        couples=couples,
        entries=entries,
        event_judges=event_judges,
        rounds=rounds,
        marks=marks,
        round_dance_results=round_dance_results,
        round_totals=round_totals,
        skating_tiebreaks=skating_tiebreaks,
    )
