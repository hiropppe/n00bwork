-- =============================================================
-- JDSF Competition Data Schema (DuckDB)
-- =============================================================
-- 設計詳細: ~/.claude/plans/jdsf-db-schema.md

-- =============================================================
-- マスタ：大会・競技
-- =============================================================
CREATE TABLE IF NOT EXISTS competitions (
    competition_id   VARCHAR PRIMARY KEY,
    name             VARCHAR NOT NULL,
    venue            VARCHAR,
    held_on          DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    event_id         VARCHAR PRIMARY KEY,
    competition_id   VARCHAR NOT NULL REFERENCES competitions(competition_id),
    seq              INTEGER NOT NULL,
    category_code    VARCHAR NOT NULL,
    category_name    VARCHAR NOT NULL,
    discipline       VARCHAR,
    age_group        VARCHAR,
    dances           VARCHAR[] NOT NULL,
    entries          INTEGER,
    couples_started  INTEGER,
    judge_count      INTEGER,
    source_url       VARCHAR,
    UNIQUE (competition_id, seq)
);

-- =============================================================
-- 人物・カップル・審判
-- =============================================================
CREATE TABLE IF NOT EXISTS persons (
    person_id        BIGINT PRIMARY KEY,
    name             VARCHAR NOT NULL,
    name_normalized  VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS person_aliases (
    canonical_id     BIGINT NOT NULL REFERENCES persons(person_id),
    alias_id         BIGINT NOT NULL REFERENCES persons(person_id),
    PRIMARY KEY (canonical_id, alias_id)
);

CREATE TABLE IF NOT EXISTS couples (
    couple_id        BIGINT PRIMARY KEY,
    leader_id        BIGINT NOT NULL REFERENCES persons(person_id),
    partner_id       BIGINT NOT NULL REFERENCES persons(person_id),
    UNIQUE (leader_id, partner_id)
);

CREATE TABLE IF NOT EXISTS judges (
    judge_id         BIGINT PRIMARY KEY,
    name             VARCHAR NOT NULL,
    name_normalized  VARCHAR NOT NULL
);

-- =============================================================
-- イベント参加情報
-- =============================================================
CREATE TABLE IF NOT EXISTS event_entries (
    event_id         VARCHAR NOT NULL REFERENCES events(event_id),
    bib_number       INTEGER NOT NULL,
    couple_id        BIGINT NOT NULL REFERENCES couples(couple_id),
    affiliation      VARCHAR,
    final_rank_label VARCHAR,
    final_rank       INTEGER,
    eliminated_round VARCHAR,
    note             VARCHAR,
    PRIMARY KEY (event_id, bib_number)
);

CREATE TABLE IF NOT EXISTS event_judges (
    event_id         VARCHAR NOT NULL REFERENCES events(event_id),
    ref_symbol       VARCHAR NOT NULL,
    judge_id         BIGINT NOT NULL REFERENCES judges(judge_id),
    venue_code       VARCHAR,
    PRIMARY KEY (event_id, ref_symbol)
);

-- =============================================================
-- ラウンド構造
-- =============================================================
CREATE TABLE IF NOT EXISTS rounds (
    round_id         BIGINT PRIMARY KEY,
    event_id         VARCHAR NOT NULL REFERENCES events(event_id),
    round_kind       VARCHAR NOT NULL,
    round_seq        INTEGER NOT NULL,
    label_jp         VARCHAR NOT NULL,
    couples_in       INTEGER,
    couples_out      INTEGER,
    recall_threshold INTEGER,
    UNIQUE (event_id, round_kind, round_seq)
);

-- =============================================================
-- ★ コア事実テーブル：ジャッジ単位の生マーク
-- =============================================================
CREATE TABLE IF NOT EXISTS judge_marks (
    event_id     VARCHAR NOT NULL,
    round_id     BIGINT NOT NULL REFERENCES rounds(round_id),
    bib_number   INTEGER NOT NULL,
    dance_code   VARCHAR NOT NULL,
    judge_ref    VARCHAR NOT NULL,
    mark_type    VARCHAR NOT NULL,
    recalled     BOOLEAN,
    placement    INTEGER,
    PRIMARY KEY (event_id, round_id, bib_number, dance_code, judge_ref)
);

-- =============================================================
-- 集計（HTML 側の値を保持・再計算検証用）
-- =============================================================
CREATE TABLE IF NOT EXISTS round_dance_results (
    event_id        VARCHAR NOT NULL,
    round_id        BIGINT NOT NULL REFERENCES rounds(round_id),
    bib_number      INTEGER NOT NULL,
    dance_code      VARCHAR NOT NULL,
    recall_total    INTEGER,
    placement_score INTEGER,
    dance_rank      INTEGER,
    decision_method VARCHAR,
    PRIMARY KEY (event_id, round_id, bib_number, dance_code)
);

CREATE TABLE IF NOT EXISTS round_totals (
    event_id    VARCHAR NOT NULL,
    round_id    BIGINT NOT NULL REFERENCES rounds(round_id),
    bib_number  INTEGER NOT NULL,
    total_score NUMERIC,
    round_rank  INTEGER,
    PRIMARY KEY (event_id, round_id, bib_number)
);

-- 規定10/11 のタイブレーク中間値（決勝のみ）
-- dance_code: 種目別なら 'W'/'T'/... 総合は '_TOTAL_' センチネル
CREATE TABLE IF NOT EXISTS skating_tiebreaks (
    event_id        VARCHAR NOT NULL,
    round_id        BIGINT NOT NULL REFERENCES rounds(round_id),
    bib_number      INTEGER NOT NULL,
    dance_code      VARCHAR NOT NULL,
    rule_no         INTEGER NOT NULL,
    cumulative      INTEGER[],
    final_rank      INTEGER,
    not_applicable  BOOLEAN,
    PRIMARY KEY (event_id, round_id, bib_number, rule_no, dance_code)
);

-- =============================================================
-- 監査
-- =============================================================
CREATE TABLE IF NOT EXISTS raw_pages (
    url           VARCHAR PRIMARY KEY,
    event_id      VARCHAR,
    fetched_at    TIMESTAMP,
    encoding      VARCHAR DEFAULT 'CP932',
    html_sha256   VARCHAR,
    raw_path      VARCHAR
);
