from __future__ import annotations

from jdsf.ids import couple_id, person_id
from jdsf.normalize import normalize_name
from jdsf.parse.ranking import parse_ranking


def test_parse_ranking_counts(fixture_soup):
    persons, couples, entries = parse_ranking(fixture_soup, event_id="260416_03")
    assert len(entries) == 15
    assert len(couples) == 15
    # 30人ぴったり（同一人物が複数組に出ていないことの確認も兼ねる）
    assert len(persons) == 30


def test_parse_ranking_first_place(fixture_soup):
    _, _, entries = parse_ranking(fixture_soup, event_id="260416_03")
    by_bib = {e.bib_number: e for e in entries}
    e = by_bib[51]
    assert e.final_rank == 1
    assert e.final_rank_label == "1"  # NFKC 正規化後
    assert e.eliminated_round is None
    # 半角カナ「ｼﾞｭﾆｱｱｽﾘｰﾄｸﾗﾌﾞ」が NFKC で全角カナへ正規化される（検索ノイズ削減のため）
    assert e.affiliation == "ジュニアアスリートクラブ"


def test_parse_ranking_couple_consistency(fixture_soup):
    persons, couples, entries = parse_ranking(fixture_soup, event_id="260416_03")
    by_bib = {e.bib_number: e for e in entries}
    by_pid = {p.person_id: p for p in persons}

    expected_leader = normalize_name("福原 聖太")
    expected_partner = normalize_name("土屋 海音")

    e = by_bib[51]
    couple = next(c for c in couples if c.couple_id == e.couple_id)
    assert by_pid[couple.leader_id].name_normalized == expected_leader
    assert by_pid[couple.partner_id].name_normalized == expected_partner

    # ID は決定論的
    assert couple.leader_id == person_id(expected_leader)
    assert couple.partner_id == person_id(expected_partner)
    assert e.couple_id == couple_id(couple.leader_id, couple.partner_id)


def test_parse_ranking_tie_at_eighth(fixture_soup):
    _, _, entries = parse_ranking(fixture_soup, event_id="260416_03")
    eighth = [e for e in entries if e.final_rank == 8]
    assert len(eighth) == 2
    assert {e.bib_number for e in eighth} == {43, 46}


def test_parse_ranking_prelim_eliminated(fixture_soup):
    _, _, entries = parse_ranking(fixture_soup, event_id="260416_03")
    prelim = [e for e in entries if e.eliminated_round == "1次予選"]
    assert len(prelim) == 5
    assert all(e.final_rank is None for e in prelim)
    assert {e.bib_number for e in prelim} == {42, 44, 45, 47, 49}
    # ラベルは元表記（NFKC 後）"1次"
    assert all(e.final_rank_label == "1次" for e in prelim)


def test_parse_ranking_no_decimal_rank(fixture_soup):
    _, _, entries = parse_ranking(fixture_soup, event_id="260416_03")
    # 10位までは決勝進出（1〜10 の各順位）+ タイ8位
    finals = [e for e in entries if e.final_rank is not None]
    assert sorted(e.final_rank for e in finals) == [1, 2, 3, 4, 5, 6, 7, 8, 8, 10]
