from __future__ import annotations

from jdsf.parse.judges import parse_judges


def test_parse_judges_count(fixture_soup):
    judges, event_judges = parse_judges(fixture_soup, event_id="260416_03")
    assert len(judges) == 7
    assert len(event_judges) == 7


def test_parse_judges_ref_and_names(fixture_soup):
    _judges, event_judges = parse_judges(fixture_soup, event_id="260416_03")
    by_ref = {ej.ref_symbol: ej for ej in event_judges}
    assert set(by_ref.keys()) == {"A", "B", "C", "D", "E", "F", "G"}


def test_parse_judges_venue_codes(fixture_soup):
    """会場識別コードは参照記号と一致しないことに注意（A,B,F,G,K,L,M）。"""
    _judges, event_judges = parse_judges(fixture_soup, event_id="260416_03")
    venue_codes = {ej.ref_symbol: ej.venue_code for ej in event_judges}
    assert venue_codes == {
        "A": "A",
        "B": "B",
        "C": "F",
        "D": "G",
        "E": "K",
        "F": "L",
        "G": "M",
    }


def test_parse_judges_names_normalized(fixture_soup):
    judges, event_judges = parse_judges(fixture_soup, event_id="260416_03")
    by_id = {j.judge_id: j for j in judges}
    name_by_ref = {
        ej.ref_symbol: by_id[ej.judge_id].name_normalized for ej in event_judges
    }
    assert name_by_ref["A"] == "水本 慶子"
    assert name_by_ref["B"] == "治面地 良和"
    assert name_by_ref["G"] == "杭田 智昭"


def test_parse_judges_event_id_propagated(fixture_soup):
    _judges, event_judges = parse_judges(fixture_soup, event_id="260416_03")
    assert all(ej.event_id == "260416_03" for ej in event_judges)
