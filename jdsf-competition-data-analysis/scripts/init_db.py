"""Initialize the JDSF DuckDB database with the schema defined in schema.sql.

Idempotent: safe to re-run on an existing database (uses CREATE TABLE IF NOT EXISTS).

Usage (inside the docker container):
    docker compose exec python uv run python scripts/init_db.py
    docker compose exec python uv run python scripts/init_db.py --db-path /data/other.duckdb
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def init_database(db_path: Path, schema_path: Path) -> list[str]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = schema_path.read_text(encoding="utf-8")

    with duckdb.connect(str(db_path)) as con:
        con.execute(schema_sql)
        rows = con.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
            """
        ).fetchall()
    return [row[0] for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the JDSF DuckDB schema.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("/data/jdsf.duckdb"),
        help="Path to the DuckDB file (default: /data/jdsf.duckdb)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parent / "schema.sql",
        help="Path to the schema SQL file",
    )
    args = parser.parse_args()

    print(f"DuckDB version: {duckdb.__version__}")
    print(f"Initializing schema in: {args.db_path}")
    print(f"Using schema file:      {args.schema}")

    tables = init_database(args.db_path, args.schema)
    print(f"\nTables present ({len(tables)}):")
    for name in tables:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
