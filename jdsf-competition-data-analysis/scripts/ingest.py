"""Ingest one JDSF page into DuckDB.

Usage:
    # ローカルファイルから（テスト・開発用）。--source-url で URL を明示
    docker compose exec python uv run python scripts/ingest.py \\
        --file tests/fixtures/R260416_03.html \\
        --source-url https://kyougi.jdsf.or.jp/2026/260416/R260416_03.html

    # URL から取得→ロード（fetch で raw も /data/raw に保存）
    docker compose exec python uv run python scripts/ingest.py \\
        --url https://kyougi.jdsf.or.jp/2026/260416/R260416_03.html
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from jdsf.fetch import decode_local_html, fetch
from jdsf.loader import load
from jdsf.models import RawPage
from jdsf.parse import parse_page


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one JDSF page into DuckDB.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", type=Path, help="Local HTML file (CP932)")
    src.add_argument("--url", help="URL to fetch and ingest")

    parser.add_argument(
        "--source-url",
        help="Source URL (required when using --file; ignored with --url)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("/data/jdsf.duckdb"),
        help="DuckDB file (default: /data/jdsf.duckdb)",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("/data/raw"),
        help="Directory to store raw HTML when fetching by URL",
    )
    args = parser.parse_args()

    if args.url:
        result = fetch(args.url, args.raw_dir)
        html = result.html
        source_url = result.url
        raw_page = RawPage(
            url=result.url,
            event_id=None,  # 後で event_id がわかったら埋める運用も検討
            fetched_at=result.fetched_at,
            encoding=result.encoding,
            html_sha256=result.sha256,
            raw_path=str(result.raw_path),
        )
    else:
        if not args.source_url:
            parser.error("--source-url is required when using --file")
        html = decode_local_html(args.file)
        source_url = args.source_url
        raw_bytes = args.file.read_bytes()
        raw_page = RawPage(
            url=source_url,
            event_id=None,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            encoding="cp932",
            html_sha256=hashlib.sha256(raw_bytes).hexdigest(),
            raw_path=str(args.file.resolve()),
        )

    page = parse_page(html, source_url=source_url, raw_page=raw_page)
    # raw_page.event_id を後付けで埋める（dataclass は frozen なので新規生成）
    page.raw_page = RawPage(
        url=raw_page.url,
        event_id=page.event.event_id,
        fetched_at=raw_page.fetched_at,
        encoding=raw_page.encoding,
        html_sha256=raw_page.html_sha256,
        raw_path=raw_page.raw_path,
    )

    with duckdb.connect(str(args.db_path)) as con:
        load(con, page)

    print(f"ingested: {page.event.event_id}  ({page.competition.name} / {page.event.category_name})")
    print(
        f"  persons={len(page.persons)} couples={len(page.couples)} "
        f"judges={len(page.judges)} entries={len(page.entries)}"
    )


if __name__ == "__main__":
    main()
