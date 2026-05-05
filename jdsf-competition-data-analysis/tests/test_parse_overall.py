from __future__ import annotations

import pytest

from jdsf.parse.overall import (
    TOTAL_DANCE_SENTINEL,
    parse_overall_finals,
    parse_skating_tiebreak,
)
from jdsf.parse.rounds import extract_round_structure


@pytest.fixture(scope="module")
def finals_round(fixture_soup):
    rounds = extract_round_structure(fixture_soup, event_id="260416_03")
    finals = [r for r in rounds if r.round_kind == "final"]
    assert len(finals) == 1
    return finals[0]


class TestOverallFinals:
    def test_seven_couples_in_finals(self, fixture_soup, finals_round):
        rdr, totals = parse_overall_finals(fixture_soup, finals_round=finals_round)
        assert len(totals) == 7  # 決勝進出は7組（タイにより8位2組）

    def test_dance_results_per_couple(self, fixture_soup, finals_round):
        # 5種目（W/T/V/F/Q）× 7組 = 35行
        rdr, _ = parse_overall_finals(fixture_soup, finals_round=finals_round)
        assert len(rdr) == 35
        codes = {r.dance_code for r in rdr}
        assert codes == {"W", "T", "V", "F", "Q"}

    def test_first_place_total_score(self, fixture_soup, finals_round):
        _, totals = parse_overall_finals(fixture_soup, finals_round=finals_round)
        by_bib = {t.bib_number: t for t in totals}
        # 背番号 51 が1位、合計 8.0
        assert by_bib[51].total_score == 8.0
        assert by_bib[51].round_rank == 1

    def test_dance_rank_for_first_place(self, fixture_soup, finals_round):
        rdr, _ = parse_overall_finals(fixture_soup, finals_round=finals_round)
        # 背番号 51 の各種目の dance_rank: W=2, T=3, V=1, F=1, Q=1
        ranks_51 = {r.dance_code: r.dance_rank for r in rdr if r.bib_number == 51}
        assert ranks_51 == {"W": 2, "T": 3, "V": 1, "F": 1, "Q": 1}

    def test_round_id_propagated(self, fixture_soup, finals_round):
        rdr, totals = parse_overall_finals(fixture_soup, finals_round=finals_round)
        assert all(r.round_id == finals_round.round_id for r in rdr)
        assert all(t.round_id == finals_round.round_id for t in totals)


class TestSkatingTiebreak:
    def test_rule_10_all_not_applicable(self, fixture_soup, finals_round):
        # このイベントでは1-9で順位確定するため規定10は全て適用外
        tbs = parse_skating_tiebreak(fixture_soup, finals_round=finals_round, rule_no=10)
        assert len(tbs) == 7
        assert all(t.not_applicable for t in tbs)
        assert all(t.cumulative is None for t in tbs)
        assert all(t.dance_code == TOTAL_DANCE_SENTINEL for t in tbs)
        assert all(t.rule_no == 10 for t in tbs)
        # final_rank は決勝総合順位を反映
        ranks = sorted(t.final_rank for t in tbs)
        assert ranks == [1, 2, 3, 4, 5, 6, 7]

    def test_rule_11_all_not_applicable(self, fixture_soup, finals_round):
        tbs = parse_skating_tiebreak(fixture_soup, finals_round=finals_round, rule_no=11)
        assert len(tbs) == 7
        assert all(t.not_applicable for t in tbs)
        assert all(t.rule_no == 11 for t in tbs)
