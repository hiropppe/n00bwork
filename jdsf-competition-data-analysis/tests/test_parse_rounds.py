from __future__ import annotations

from jdsf.parse.rounds import extract_round_structure


def test_round_structure_three_rounds(fixture_soup):
    rounds = extract_round_structure(fixture_soup, event_id="260416_03")
    assert len(rounds) == 3


def test_round_structure_seq_assignment(fixture_soup):
    rounds = extract_round_structure(fixture_soup, event_id="260416_03")
    by_seq = {r.round_seq: r for r in rounds}
    assert by_seq[1].round_kind == "prelim"
    assert by_seq[1].label_jp == "1次予選"
    assert by_seq[2].round_kind == "semifinal"
    assert by_seq[2].label_jp == "準決勝"
    assert by_seq[3].round_kind == "final"
    assert by_seq[3].label_jp == "決勝"


def test_round_ids_are_distinct(fixture_soup):
    rounds = extract_round_structure(fixture_soup, event_id="260416_03")
    ids = {r.round_id for r in rounds}
    assert len(ids) == 3


def test_event_id_propagated(fixture_soup):
    rounds = extract_round_structure(fixture_soup, event_id="260416_03")
    assert all(r.event_id == "260416_03" for r in rounds)
