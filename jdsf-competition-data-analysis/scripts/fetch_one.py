"""Fetch a single JDSF page and store the raw bytes locally.

DB には書き込まない。パース・ロード前の素材取得用。

Usage:
    docker compose exec python uv run python scripts/fetch_one.py <URL>
    docker compose exec python uv run python scripts/fetch_one.py <URL> --raw-dir /data/raw
"""

from __future__ import annotations

import argparse
from pathlib import Path

from jdsf.fetch import fetch


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch one JDSF page and save raw bytes.")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("/data/raw"),
        help="Directory to store raw HTML (default: /data/raw)",
    )
    args = parser.parse_args()

    result = fetch(args.url, args.raw_dir)
    print(f"URL:        {result.url}")
    print(f"saved to:   {result.raw_path}")
    print(f"size:       {len(result.raw_bytes):,} bytes")
    print(f"encoding:   {result.encoding}")
    print(f"sha256:     {result.sha256}")
    print(f"fetched_at: {result.fetched_at}")
    # 先頭だけ表示して文字化けがないか目視確認できるようにする
    snippet = result.html[:200].replace("\n", " ")
    print(f"head[200]:  {snippet}")


if __name__ == "__main__":
    main()
