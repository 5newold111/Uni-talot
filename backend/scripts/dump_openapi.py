"""
docs/openapi.json を生成するスクリプト。

API スキーマ変更時に実行:
    cd backend
    python scripts/dump_openapi.py

CI では openapi.json がコミットされたスキーマと一致するかチェックする想定。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"


def main_cli():
    spec = main.app.openapi()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(json.dumps(spec))} bytes)")
    print("Paths:", list(spec["paths"].keys()))


if __name__ == "__main__":
    main_cli()
