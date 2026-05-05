from __future__ import annotations

import pytest

from jdsf.parse.judges import parse_judges
from jdsf.parse.per_dance import parse_per_dance
from jdsf.parse.rounds import extract_round_structure


@pytest.fixture(scope="module")
def finals_round_and_judges(fixture_soup):
    rounds = extract_round_structure(fixture_soup, event_id="260416_03")
    finals = next(r for r in rounds if r.round_kind == "final")
    _, event_judges = parse_judges(fixture_soup, event_id="260416_03")
    return finals, event_judges


def test_total_judge_marks_count(fixture_soup, finals_round_and_judges):
    """7組 × 5種目 × 7審判 = 245 行"""
    finals, ejs = finals_round_and_judges
    marks, _ = parse_per_dance(fixture_soup, finals_round=finals, event_judges=ejs)
    assert len(marks) == 245


def test_all_marks_are_placement(fixture_soup, finals_round_and_judges):
    finals, ejs = finals_round_and_judges
    marks, _ = parse_per_dance(fixture_soup, finals_round=finals, event_judges=ejs)
    assert all(m.mark_type == "placement" for m in marks)
    assert all(m.placement is not None and 1 <= m.placement <= 7 for m in marks)
    assert all(m.recalled is None for m in marks)


def test_dance_codes_covered(fixture_soup, finals_round_and_judges):
    finals, ejs = finals_round_and_judges
    marks, _ = parse_per_dance(fixture_soup, finals_round=finals, event_judges=ejs)
    assert {m.dance_code for m in marks} == {"W", "T", "V", "F", "Q"}


def test_judge_refs_covered(fixture_soup, finals_round_and_judges):
    finals, ejs = finals_round_and_judges
    marks, _ = parse_per_dance(fixture_soup, finals_round=finals, event_judges=ejs)
    assert {m.judge_ref for m in marks} == {"A", "B", "C", "D", "E", "F", "G"}


def test_specific_marks_for_bib_41_waltz(fixture_soup, finals_round_and_judges):
    """背番号41のWaltzは A=3 B=3 C=6 D=1 E=6 F=2 G=2"""
    finals, ejs = finals_round_and_judges
    marks, _ = parse_per_dance(fixture_soup, finals_round=finals, event_judges=ejs)
    bib41_W = {m.judge_ref: m.placement for m in marks if m.bib_number == 41 and m.dance_code == "W"}
    assert bib41_W == {"A": 3, "B": 3, "C": 6, "D": 1, "E": 6, "F": 2, "G": 2}


def test_decision_methods(fixture_soup, finals_round_and_judges):
    finals, ejs = finals_round_and_judges
    _, decisions = parse_per_dance(fixture_soup, finals_round=finals, event_judges=ejs)
    # 背番号53のWaltzは「上位加算」（タイ判定が必要だった）
    assert decisions[(53, "W")] == "上位加算"
    # 背番号41のWaltzは「多数決」
    assert decisions[(41, "W")] == "多数決"
