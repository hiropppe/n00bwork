from __future__ import annotations

import pytest

from jdsf.parse.judges import parse_judges
from jdsf.parse.rounds import extract_round_structure, parse_round_details


@pytest.fixture(scope="module")
def rounds_and_judges(fixture_soup):
    rounds = extract_round_structure(fixture_soup, event_id="260416_03")
    _, event_judges = parse_judges(fixture_soup, event_id="260416_03")
    return rounds, event_judges


def test_marks_only_recall_no_final(fixture_soup, rounds_and_judges):
    """決勝行は per_dance 経由で取得済みのため、Section 8 では recall のみ。"""
    rounds, ejs = rounds_and_judges
    marks, _ = parse_round_details(fixture_soup, rounds=rounds, event_judges=ejs)
    assert all(m.mark_type == "recall" for m in marks)
    assert all(m.placement is None for m in marks)
    assert all(isinstance(m.recalled, bool) for m in marks)


def test_marks_total_count(fixture_soup, rounds_and_judges):
    """予選: 15組×5種目×7審判 = 525
    準決勝: 10組×5種目×7審判 = 350
    合計: 875
    """
    rounds, ejs = rounds_and_judges
    marks, _ = parse_round_details(fixture_soup, rounds=rounds, event_judges=ejs)
    by_kind: dict[str, int] = {}
    rounds_by_id = {r.round_id: r for r in rounds}
    for m in marks:
        kind = rounds_by_id[m.round_id].round_kind
        by_kind[kind] = by_kind.get(kind, 0) + 1
    assert by_kind.get("prelim") == 15 * 5 * 7
    assert by_kind.get("semifinal") == 10 * 5 * 7
    assert "final" not in by_kind  # 決勝はスキップ


def test_recall_total_matches_count_of_O(fixture_soup, rounds_and_judges):
    """recall_total は recalled=True の数と一致するべき"""
    rounds, ejs = rounds_and_judges
    marks, rdrs = parse_round_details(fixture_soup, rounds=rounds, event_judges=ejs)

    # 各 (round_id, bib, dance) のグループの O 数 と recall_total を比較
    o_counts: dict[tuple[int, int, str], int] = {}
    for m in marks:
        key = (m.round_id, m.bib_number, m.dance_code)
        if m.recalled:
            o_counts[key] = o_counts.get(key, 0) + 1

    for r in rdrs:
        key = (r.round_id, r.bib_number, r.dance_code)
        assert r.recall_total == o_counts.get(key, 0), (
            f"recall_total mismatch for {key}: HTML={r.recall_total}, computed={o_counts.get(key, 0)}"
        )


def test_specific_recall_for_bib_51_prelim_waltz(fixture_soup, rounds_and_judges):
    """背番号51 の１次予選 Waltz は OO-OOO-（A=O B=O C=X D=O E=O F=O G=X、合計5）"""
    rounds, ejs = rounds_and_judges
    marks, _ = parse_round_details(fixture_soup, rounds=rounds, event_judges=ejs)
    prelim = next(r for r in rounds if r.round_kind == "prelim" and r.round_seq == 1)
    bib51 = {
        m.judge_ref: m.recalled
        for m in marks
        if m.bib_number == 51 and m.dance_code == "W" and m.round_id == prelim.round_id
    }
    assert bib51 == {"A": True, "B": True, "C": False, "D": True, "E": True, "F": True, "G": False}
