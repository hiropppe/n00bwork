"""DuckDB writer for ParsedPage.

イベント単位の冪等再投入をサポート：
  1. 子テーブルから順に DELETE WHERE event_id = ?
  2. 親テーブルへ INSERT
  3. persons/judges/couples/competitions は ON CONFLICT DO NOTHING（または UPDATE）
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import duckdb

from jdsf.models import (
    Competition,
    Couple,
    Event,
    EventEntry,
    EventJudge,
    Judge,
    JudgeMark,
    ParsedPage,
    Person,
    RawPage,
    Round,
    RoundDanceResult,
    RoundTotal,
    SkatingTiebreak,
)


# 削除順序（子→親）。FK 制約のため厳守。
_EVENT_SCOPED_TABLES_DELETE_ORDER = (
    "skating_tiebreaks",
    "round_totals",
    "round_dance_results",
    "judge_marks",
    "rounds",
    "event_judges",
    "event_entries",
    "events",
)


def load(con: duckdb.DuckDBPyConnection, page: ParsedPage) -> None:
    """ParsedPage を DuckDB にロード（冪等）。

    DuckDB の FK 制約は同一トランザクション内の DELETE を即座に可視化しないため、
    DELETE はオートコミットで先に実行する。INSERT 群はトランザクションで原子化。
    DELETE 後に INSERT が失敗した場合はデータ欠落になるが、再実行で回復する設計。
    """
    # 1) DELETE は autocommit（FK 制約のトランザクション内可視性問題を回避）
    _delete_event_scope(con, page.event.event_id)

    # 2) INSERT 群はトランザクション内で原子化
    con.begin()
    try:
        _upsert_competition(con, page.competition)
        _upsert_persons(con, page.persons)
        _upsert_couples(con, page.couples)
        _upsert_judges(con, page.judges)
        _insert_event(con, page.event)
        _insert_event_entries(con, page.entries)
        _insert_event_judges(con, page.event_judges)
        _insert_rounds(con, page.rounds)
        _insert_judge_marks(con, page.marks)
        _insert_round_dance_results(con, page.round_dance_results)
        _insert_round_totals(con, page.round_totals)
        _insert_skating_tiebreaks(con, page.skating_tiebreaks)
        if page.raw_page is not None:
            _upsert_raw_page(con, page.raw_page)
        con.commit()
    except Exception:
        con.rollback()
        raise


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


def _delete_event_scope(con: duckdb.DuckDBPyConnection, event_id: str) -> None:
    for table in _EVENT_SCOPED_TABLES_DELETE_ORDER:
        con.execute(f"DELETE FROM {table} WHERE event_id = ?", [event_id])


# ---------------------------------------------------------------------------
# UPSERT helpers
# ---------------------------------------------------------------------------


def _upsert_competition(con: duckdb.DuckDBPyConnection, c: Competition) -> None:
    con.execute(
        """
        INSERT INTO competitions (competition_id, name, venue, held_on)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (competition_id) DO UPDATE SET
            name = EXCLUDED.name,
            venue = EXCLUDED.venue,
            held_on = EXCLUDED.held_on
        """,
        [c.competition_id, c.name, c.venue, c.held_on],
    )


def _upsert_persons(con: duckdb.DuckDBPyConnection, persons: Iterable[Person]) -> None:
    rows = [(p.person_id, p.name, p.name_normalized) for p in persons]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO persons (person_id, name, name_normalized)
        VALUES (?, ?, ?)
        ON CONFLICT (person_id) DO NOTHING
        """,
        rows,
    )


def _upsert_couples(con: duckdb.DuckDBPyConnection, couples: Iterable[Couple]) -> None:
    rows = [(c.couple_id, c.leader_id, c.partner_id) for c in couples]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO couples (couple_id, leader_id, partner_id)
        VALUES (?, ?, ?)
        ON CONFLICT (couple_id) DO NOTHING
        """,
        rows,
    )


def _upsert_judges(con: duckdb.DuckDBPyConnection, judges: Iterable[Judge]) -> None:
    rows = [(j.judge_id, j.name, j.name_normalized) for j in judges]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO judges (judge_id, name, name_normalized)
        VALUES (?, ?, ?)
        ON CONFLICT (judge_id) DO NOTHING
        """,
        rows,
    )


def _upsert_raw_page(con: duckdb.DuckDBPyConnection, rp: RawPage) -> None:
    con.execute(
        """
        INSERT INTO raw_pages (url, event_id, fetched_at, encoding, html_sha256, raw_path)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (url) DO UPDATE SET
            event_id = EXCLUDED.event_id,
            fetched_at = EXCLUDED.fetched_at,
            encoding = EXCLUDED.encoding,
            html_sha256 = EXCLUDED.html_sha256,
            raw_path = EXCLUDED.raw_path
        """,
        [rp.url, rp.event_id, rp.fetched_at, rp.encoding, rp.html_sha256, rp.raw_path],
    )


# ---------------------------------------------------------------------------
# INSERT (event-scoped)
# ---------------------------------------------------------------------------


def _insert_event(con: duckdb.DuckDBPyConnection, e: Event) -> None:
    con.execute(
        """
        INSERT INTO events (
            event_id, competition_id, seq, category_code, category_name,
            discipline, age_group, dances, entries, couples_started,
            judge_count, source_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            e.event_id,
            e.competition_id,
            e.seq,
            e.category_code,
            e.category_name,
            e.discipline,
            e.age_group,
            list(e.dances),
            e.entries,
            e.couples_started,
            e.judge_count,
            e.source_url,
        ],
    )


def _insert_event_entries(
    con: duckdb.DuckDBPyConnection, entries: Iterable[EventEntry]
) -> None:
    rows: list[tuple[Any, ...]] = [
        (
            ee.event_id,
            ee.bib_number,
            ee.couple_id,
            ee.affiliation,
            ee.final_rank_label,
            ee.final_rank,
            ee.eliminated_round,
            ee.note,
        )
        for ee in entries
    ]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO event_entries (
            event_id, bib_number, couple_id, affiliation,
            final_rank_label, final_rank, eliminated_round, note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_event_judges(
    con: duckdb.DuckDBPyConnection, event_judges: Iterable[EventJudge]
) -> None:
    rows = [
        (ej.event_id, ej.ref_symbol, ej.judge_id, ej.venue_code) for ej in event_judges
    ]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO event_judges (event_id, ref_symbol, judge_id, venue_code)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )


def _insert_rounds(con: duckdb.DuckDBPyConnection, rounds: Iterable[Round]) -> None:
    rows = [
        (
            r.round_id,
            r.event_id,
            r.round_kind,
            r.round_seq,
            r.label_jp,
            r.couples_in,
            r.couples_out,
            r.recall_threshold,
        )
        for r in rounds
    ]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO rounds (
            round_id, event_id, round_kind, round_seq, label_jp,
            couples_in, couples_out, recall_threshold
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_judge_marks(
    con: duckdb.DuckDBPyConnection, marks: Iterable[JudgeMark]
) -> None:
    rows = [
        (
            m.event_id,
            m.round_id,
            m.bib_number,
            m.dance_code,
            m.judge_ref,
            m.mark_type,
            m.recalled,
            m.placement,
        )
        for m in marks
    ]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO judge_marks (
            event_id, round_id, bib_number, dance_code, judge_ref,
            mark_type, recalled, placement
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_round_dance_results(
    con: duckdb.DuckDBPyConnection, results: Iterable[RoundDanceResult]
) -> None:
    rows = [
        (
            r.event_id,
            r.round_id,
            r.bib_number,
            r.dance_code,
            r.recall_total,
            r.placement_score,
            r.dance_rank,
            r.decision_method,
        )
        for r in results
    ]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO round_dance_results (
            event_id, round_id, bib_number, dance_code,
            recall_total, placement_score, dance_rank, decision_method
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_round_totals(
    con: duckdb.DuckDBPyConnection, totals: Iterable[RoundTotal]
) -> None:
    rows = [
        (rt.event_id, rt.round_id, rt.bib_number, rt.total_score, rt.round_rank)
        for rt in totals
    ]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO round_totals (
            event_id, round_id, bib_number, total_score, round_rank
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_skating_tiebreaks(
    con: duckdb.DuckDBPyConnection, tiebreaks: Iterable[SkatingTiebreak]
) -> None:
    rows = [
        (
            t.event_id,
            t.round_id,
            t.bib_number,
            t.dance_code,
            t.rule_no,
            list(t.cumulative) if t.cumulative is not None else None,
            t.final_rank,
            t.not_applicable,
        )
        for t in tiebreaks
    ]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO skating_tiebreaks (
            event_id, round_id, bib_number, dance_code, rule_no,
            cumulative, final_rank, not_applicable
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
