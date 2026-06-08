#!/usr/bin/env python3
"""アルバムリリース（配信パッケージ生成）を実行する。

毎月 1 日・15 日に GitHub Actions から起動される想定。
ローカル確認では --force でリリース日チェックを無視して実行できる。

Usage:
    python scripts/run_release.py [--force] [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from music_pipeline.pipeline import Pipeline, configure_logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Album release packaging")
    parser.add_argument("--force", action="store_true", help="リリース日チェックを無視して実行")
    parser.add_argument("--date", type=str, default=None, help="リリース日 YYYY-MM-DD")
    parser.add_argument(
        "--upload",
        choices=["none", "playwright"],
        default="none",
        help="none=半自動（既定）, playwright=ブラウザ自動操作で DistroKid へ投入",
    )
    args = parser.parse_args()

    release_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()

    configure_logging()
    pipeline = Pipeline()
    album = pipeline.run_release(release_date=release_date, force=args.force, upload=args.upload)
    if album is None:
        print("No release produced (not a release day, or no unreleased tracks).")
    else:
        print(f"Released album '{album.title}' -> {album.package_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
