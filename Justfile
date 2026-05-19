# EC3D-Bridge 開発タスク。`just` (https://github.com/casey/just) で実行。

default:
    @just --list

# === Test ===
# バックエンド + 拡張機能のすべてのテストを実行
test: test-backend test-extension

# pytest を実行 (カバレッジ付き)
test-backend:
    cd backend && pytest tests/ --cov --cov-report=term

# Node --test を実行
test-extension:
    cd extension && node --test tests/test_scraper.mjs tests/test_e2e_scraper.mjs

# === Lint / Format ===
# 全 lint
lint: lint-backend lint-manifest

# ruff check + format --check
lint-backend:
    cd backend && ruff check . && ruff format --check .

# manifest.json を検証
lint-manifest:
    python3 -c "import json; json.load(open('extension/manifest.json'))"

# ruff で自動整形 (in-place)
fmt:
    cd backend && ruff format . && ruff check --fix .

# === Dev server ===
# バックエンド開発サーバー起動 (reload あり)
serve:
    cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 3000

# Docker Compose で起動 (Blender + Playwright 入りイメージ)
serve-docker:
    docker compose up --build

# === OpenAPI / Docs ===
# docs/openapi.json を再生成
openapi:
    cd backend && python3 scripts/dump_openapi.py

# README の popup スクショを再生成 (Pillow ベース mockup)
screenshot:
    python3 scripts/render_popup_screenshot.py

# === Setup ===
# 依存関係をインストール
install:
    cd backend && pip install -r requirements-dev.txt && python -m playwright install chromium
    cd extension && npm install

# pre-commit を有効化
hooks:
    pre-commit install
