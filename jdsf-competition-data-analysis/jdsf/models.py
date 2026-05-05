"""DTOs representing parsed JDSF page data.

各 dataclass は schema.sql のテーブルと 1 対 1 対応する（または近い形）。
loader.py はこれらを INSERT 文に変換する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True, slots=True)
class Competition:
    competition_id: str
    name: str
    venue: str | None
    held_on: date


@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    competition_id: str
    seq: int
    category_code: str
    category_name: str
    discipline: str | None
    age_group: str | None
    dances: tuple[str, ...]
    entries: int | None
    couples_started: int | None
    judge_count: int | None
    source_url: str | None


@dataclass(frozen=True, slots=True)
class Person:
    person_id: int
    name: str
    name_normalized: str


@dataclass(frozen=True, slots=True)
class Couple:
    couple_id: int
    leader_id: int
    partner_id: int


@dataclass(frozen=True, slots=True)
class Judge:
    judge_id: int
    name: str
    name_normalized: str


@dataclass(frozen=True, slots=True)
class EventEntry:
    event_id: str
    bib_number: int
    couple_id: int
    affiliation: str | None
    final_rank_label: str | None
    final_rank: int | None
    eliminated_round: str | None
    note: str | None


@dataclass(frozen=True, slots=True)
class EventJudge:
    event_id: str
    ref_symbol: str
    judge_id: int
    venue_code: str | None


@dataclass(frozen=True, slots=True)
class Round:
    round_id: int
    event_id: str
    round_kind: str  # 'prelim' | 'semifinal' | 'final'
    round_seq: int
    label_jp: str
    couples_in: int | None
    couples_out: int | None
    recall_threshold: int | None


@dataclass(frozen=True, slots=True)
class JudgeMark:
    event_id: str
    round_id: int
    bib_number: int
    dance_code: str
    judge_ref: str
    mark_type: str  # 'recall' | 'placement'
    recalled: bool | None
    placement: int | None


@dataclass(frozen=True, slots=True)
class RoundDanceResult:
    event_id: str
    round_id: int
    bib_number: int
    dance_code: str
    recall_total: int | None
    placement_score: int | None
    dance_rank: int | None
    decision_method: str | None


@dataclass(frozen=True, slots=True)
class RoundTotal:
    event_id: str
    round_id: int
    bib_number: int
    total_score: float | None
    round_rank: int | None


@dataclass(frozen=True, slots=True)
class SkatingTiebreak:
    event_id: str
    round_id: int
    bib_number: int
    dance_code: str  # 'W' / 'T' / ... または '_TOTAL_'（総合）
    rule_no: int
    cumulative: tuple[int, ...] | None
    final_rank: int | None
    not_applicable: bool


@dataclass(frozen=True, slots=True)
class RawPage:
    url: str
    event_id: str | None
    fetched_at: str  # ISO 8601 タイムスタンプ
    encoding: str
    html_sha256: str
    raw_path: str | None


@dataclass(slots=True)
class ParsedPage:
    """1ページのパース結果を集約するコンテナ。"""

    competition: Competition
    event: Event
    raw_page: RawPage | None = None
    persons: list[Person] = field(default_factory=list)
    judges: list[Judge] = field(default_factory=list)
    couples: list[Couple] = field(default_factory=list)
    entries: list[EventEntry] = field(default_factory=list)
    event_judges: list[EventJudge] = field(default_factory=list)
    rounds: list[Round] = field(default_factory=list)
    marks: list[JudgeMark] = field(default_factory=list)
    round_dance_results: list[RoundDanceResult] = field(default_factory=list)
    round_totals: list[RoundTotal] = field(default_factory=list)
    skating_tiebreaks: list[SkatingTiebreak] = field(default_factory=list)
