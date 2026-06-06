#!/usr/bin/env python3
"""日次の楽曲生成を実行する（既定 3 曲）。

Usage:
    python scripts/run_daily.py [--count N]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from music_pipeline.pipeline import Pipeline, configure_logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily song generation")
    parser.add_argument("--count", type=int, default=None, help="生成する曲数（既定: config の songs_per_day）")
    args = parser.parse_args()

    configure_logging()
    pipeline = Pipeline()
    generated = pipeline.run_daily(count=args.count)
    print(f"Generated {len(generated)} track(s): {generated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
