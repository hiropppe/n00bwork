from __future__ import annotations

from datetime import date

from jdsf.parse.header import parse_header


def test_parse_header_competition(fixture_soup, fixture_url):
    competition, _event = parse_header(fixture_soup, source_url=fixture_url)
    assert competition.competition_id == "260416"
    assert competition.name == "2026ダンススポーツグランプリin京都"
    assert competition.venue == "西宇治体育館"
    assert competition.held_on == date(2026, 4, 19)


def test_parse_header_event(fixture_soup, fixture_url):
    _competition, event = parse_header(fixture_soup, source_url=fixture_url)
    assert event.event_id == "260416_03"
    assert event.competition_id == "260416"
    assert event.seq == 3
    # NFKC で 'ＸＪＳ' → 'XJS'
    assert event.category_code == "XJS"
    assert event.category_name == "ジュニア スタンダード"
    assert event.dances == ("W", "T", "V", "F", "Q")
    assert event.entries == 15
    assert event.couples_started == 15
    assert event.judge_count == 7
    assert event.source_url == fixture_url
