# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

JDSF（公益社団法人 日本ダンススポーツ連盟）の競技会結果ページをスクレイピング・構造化し、DuckDB に格納して **独自ランキング、メトリクス、審査員バイアス・ばらつきの統計分析** を行うプロジェクト。最重要視点は「ジャッジ単位の生マーク（O/X リコール、決勝の placement）」の保存。

データソース URL パターン:
```
https://kyougi.jdsf.or.jp/YYYY/{permit_id}/R{permit_id}_{seq}.html
```
1ページ = 1イベント（大会×種別の組み合わせ）。

詳細な設計プランは `~/.claude/plans/` に：
- `jdsf-db-schema.md` — スキーマ設計
- `jdsf-parser.md` — パーサ設計

## 開発環境

Docker Compose の2サービス構成:
- `python`: Python 3.13 + uv（編集モードでパッケージインストール、`/workspace/.venv` に環境）
- `duckdb`: DuckDB CLI 専用（`sleep infinity` で待機）

両サービスとも `./data/` を bind mount し、DuckDB ファイル（`./data/jdsf.duckdb`）はホスト側からも DBeaver 等で参照可。

## 常用コマンド

```bash
# 起動・停止
docker compose up -d --build
docker compose down

# テスト（全件）
docker compose exec python uv run pytest

# テスト（単体ファイル / 単体関数）
docker compose exec python uv run pytest tests/test_parse_overall.py
docker compose exec python uv run pytest tests/test_parse_overall.py::TestOverallFinals::test_first_place_total_score -v

# Lint
docker compose exec python uv run ruff check .
docker compose exec python uv run ruff format .

# DB 初期化（冪等：CREATE TABLE IF NOT EXISTS）
docker compose exec python uv run python scripts/init_db.py

# 1ページ取り込み（ローカルファイル）
docker compose exec python uv run python scripts/ingest.py \
    --file tests/fixtures/R260416_03.html \
    --source-url https://kyougi.jdsf.or.jp/2026/260416/R260416_03.html

# 1ページ取り込み（URL から fetch）
docker compose exec python uv run python scripts/ingest.py \
    --url https://kyougi.jdsf.or.jp/2026/260416/R260416_03.html

# DuckDB CLI（インタラクティブ）
docker compose exec duckdb duckdb /data/jdsf.duckdb
```

## アーキテクチャ

```
HTML(CP932) ── fetch ──▶ str ── parse(8セクション) ──▶ ParsedPage(DTO群) ── load ──▶ DuckDB
```

3層に疎結合（fetch / parse / load）。テストはローカル fixture（`tests/fixtures/R260416_03.html`）から parse のみを検証可能。

### パッケージ構成（要点のみ）

- `jdsf/parse/` — セクション単位の関数群。1ページに 8 セクションあるため、対応する 6 ファイルに分割（`header / ranking / judges / overall / per_dance / rounds`）。各ファイルは「テーブル発見 → ヘッダ解釈 → 行ループ」の同じパターン。
- `jdsf/parse/__init__.py::parse_page` — 全セクションを束ねる中央エントリポイント。決勝ラウンドが見つかった場合のみ Section 4-7 を呼ぶ条件分岐がある。
- `jdsf/models.py::ParsedPage` — パース結果の集約コンテナ。`loader.load(con, page)` が受け取って書き込む。
- `jdsf/loader.py` — DuckDB 書き込み。**冪等性の鍵は `_delete_event_scope` を「トランザクション外」で実行すること**（後述）。
- `jdsf/ids.py` — SHA256 上位 8 バイト → 63bit の決定論的 BIGINT。`person_id` / `judge_id` / `couple_id` / `round_id` を生成。**同じ入力で同じ ID** が返るので、複数大会の取り込みでエンティティが自然にマージされる。
- `scripts/schema.sql` — 14 テーブル DDL。中央事実テーブルは `judge_marks`（event×round×bib×dance×judge の最小粒度、`mark_type='recall'|'placement'`）。
- `scripts/init_db.py` / `scripts/ingest.py` / `scripts/fetch_one.py` — CLI エントリ。

### 設計上の重要な不変条件

1. **生マーク第一**: `judge_marks` を最も粒度の細かい事実テーブルとし、規定1〜11 の集計値（`round_dance_results` / `round_totals` / `skating_tiebreaks`）はそこから再計算検証可能な派生として保持。
2. **冪等再投入**: 同 URL の再取り込みでは `event_id` スコープで DELETE → INSERT。`competitions` / `persons` / `couples` / `judges` は ON CONFLICT DO NOTHING（または UPDATE）で蓄積。
3. **fail-fast**: 想定外の HTML 構造（未知の種目コード、欠損ヘッダ、空の判子テーブル等）は例外で停止する。黙って取り込まない。
4. **元 HTML 保持**: `raw_pages` テーブル + `/data/raw/` 配下にバイト列をそのまま保存。パーサ更新時に再パース可能。

## 知見・注意点

### DuckDB の癖

- **トランザクション内の FK 制約は in-flight DELETE を可視化しない**。子テーブルから順に DELETE しても、親テーブルへの DELETE で「key is still referenced」エラーになる。
  - 解決: `loader.load()` は DELETE をオートコミット（トランザクション外）で先に実行し、INSERT 群のみトランザクション内で原子化する。
  - 失敗時の挙動: DELETE 後に INSERT が失敗するとデータ欠落になるが、再実行で回復する設計（冪等性が前提）。
- **CLI バイナリのアセット命名はバージョンで違う**。v1.5+ は `linux-amd64.zip` / `linux-arm64.zip`、v1.1.x 以前は `linux-aarch64.zip`。`docker/duckdb/Dockerfile` の `DUCKDB_VERSION` を変更する場合はアセット命名を要確認。
- **PRIMARY KEY に式（`COALESCE` 等）は使えない**。NULL を含めたい列はセンチネル値で代替。`skating_tiebreaks.dance_code` は総合の場合 `'_TOTAL_'`（種目別は `'W'` 等）を入れる。
- **配列型 `INTEGER[]` / `VARCHAR[]` は Python の list でそのまま渡せる**（`con.execute("INSERT ... VALUES (?)", [['W','T']])`）。

### JDSF ページの扱い

- **エンコーディングは CP932**。`iconv -f SHIFT_JIS` だと不正バイトで失敗するので、必ず `cp932` を使う（Python: `bytes.decode("cp932")`）。
- **HTML は閉じタグ欠落だらけ**（`</TR>` `</TD>` 抜け）。lxml バックエンドが補完するが、`<table>` の境界を文字列マーカー（`■`, `●`）で起点にして探すのが堅い。
- **NFKC 正規化を全文字列に通す**（`jdsf/normalize.py`）。'Ｗ' → 'W'、'ｼﾞｭﾆｱ' → 'ジュニア'、'１次' → '1次'。所属の半角カナ vs 全角カナの揺れを解消。
- **順位ラベルは数値とは限らない**。'1' / '8'（タイ）/ '1次'（１次予選敗退）等。`event_entries.final_rank_label` に元表記、`final_rank` には数値化できれば設定。
- **「決勝」の `endswith` 判定は「準決勝」にも一致する**ので、長いキーワードから先に判定する（`rounds.py::_ROUND_HEADERS = ("準決勝", "決勝")`）。
- **Section 8 の決勝行は `per_dance` で取得済みのためスキップ**する設計。重複防止。

### ID 生成

- 名寄せは段階導入。第一段階は「氏名 NFKC 正規化」のみで `person_id` を計算。同姓同名は重複として後で `person_aliases` で統合する。
- `person_id` と `judge_id` は名前空間を分離（`_hash_to_bigint("person", ...)` と `"judge"` プレフィックス）。万一の同名混在で衝突しないように。
- `couple_id` は `(leader_id, partner_id)` の順序を保持（役割を入れ替えると別カップル ID）。

## テスト

- すべてローカル fixture（`tests/fixtures/R260416_03.html`、CP932 のまま）を使用。fixture のロードは `tests/conftest.py` が session スコープで提供（`fixture_html` / `fixture_soup` / `fixture_url`）。
- 期待値は fixture の中身に依存（例：1位は背番号 51、合計 8.0、決勝マーク 245 行等）。fixture を差し替えるとテストも修正が必要。
- 検証用の代表値:
  - `event_entries` = 15、決勝進出 7 組（タイ 8 位 2 組）、予選敗退 5 組
  - `judge_marks` = 1120（決勝 placement 245 + 予選 recall 525 + 準決勝 recall 350）
  - 1位（背番号 51 福原 聖太 / 土屋 海音）の決勝 `total_score` = 8.0
