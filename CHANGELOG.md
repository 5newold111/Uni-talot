# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.2] - 2026-05-22

### Added
- popup_utils.js: timeAgo / escapeHtml / parseBulkUrls / statusBadgeClass を切り出し、
  popup.js とテストの両方から利用可能に
- 17 件の popup ヘルパー単体テスト (`tests/test_popup_utils.mjs`):
  - timeAgo の秒/分/時間/日/未来分岐
  - escapeHtml の XSS / 二重エスケープ / 非文字列キャスト
  - parseBulkUrls の空行スキップ / javascript:・data: 弾き
  - statusBadgeClass の既知/未知ハンドリング
- 11 件の homestyler_bot 単体テスト (`tests/test_homestyler_unit.py`):
  - SELECTORS 辞書の整合性 (必須キー、CSV 形式)
  - _find_element のフォールバック挙動 (最初の可視を返す/全部不可視/例外スキップ/空白trim)
  - upload_to_homestyler の事前検証 (email/password/GLB 不在)
  - スクリーンショットファイル名のサニタイズ
  - Semaphore のデフォルト容量
- 9 件のサーバースモークテスト (`tests/test_smoke.py`):
  - 全 7 エンドポイントが FastAPI に登録されている
  - /output 静的マウントが有効
  - /openapi.json / /docs (Swagger UI) が応答
  - 単発投入→ status→ jobs→ cancel→ guidance のフルフロー
  - 404/405/CORS リーク防止

### Changed
- popup.js / popup_utils.js を分離。popup.js は DOM 操作専念、純関数は utils に集約
- index.html に popup_utils.js 読み込みを追加 (popup.js の前にロード)
- CI が test_popup_utils.mjs も実行

### Metrics
- backend テスト: 89 → **109** (+20)
- extension テスト: 20 → **37** (+17)
- 合計テスト: **146**
- カバレッジ: 84% → **86%** (homestyler_bot: 34% → 46%)

## [1.0.1] - 2026-05-22

### Fixed
- **Blender 4.0+ で `bpy.ops.export_scene.gltf` の `export_selected` 引数が削除されていた**
  ため `scale_model.py` が実行時 TypeError でクラッシュしていた。引数を削除して回避。
  この問題は実 Blender バイナリで実行して初めて顕在化したもの (subprocess.run をモック
  したユニットテストでは検出不可能だった)。

### Added
- `backend/scripts/verify_dependencies.py`: Blender / Tripo (fal.ai) / Homestyler の
  疎通・認証を最小コードで実検証する CLI (`--blender / --tripo / --homestyler / --all`)
- `tests/test_blender_integration.py`: 実 Blender バイナリで `scale_model.py` と
  `apply_real_scale` を回帰テスト (2件)。Blender 未インストールなら自動 skip
- CI が `apt install blender python3-numpy` で Blender 4.0+ を入れて統合テストも走らせる
- README に「本番依存の検証ステータス」セクションを追加 (Blender ✅ / Tripo・Homestyler 未検証)

### Verified
- ✅ Blender 4.0.2 で 20cm 立方体 → W80×D40×H75cm 補正を実走確認
- ✅ scale_correction サービス層経由でも同様に正しい寸法

## [1.0.0] - 2026-05-20

初版安定リリース。コアパイプライン (画像DL → 3D生成 → スケール補正 → Homestyler アップロード) と運用必要機能が一通り揃った状態。

### Added
- `POST /api/jobs/{job_id}/cancel` 実行中ジョブへのキャンセル要求 API
- `Job.cancel_requested` カラム (SQLite ALTER で旧DB互換マイグレーション)
- パイプラインがステップ境界で `_abort_if_cancelled` をチェックし、`status=cancelled` で終端
- popup 履歴タブにキャンセルボタン (queued/running のジョブのみ)
- `cancelled` バッジ用 CSS
- 構造化ログ統合: `logger.info(..., extra={"job_id": ...})` で JSON ログに job_id / error_code フィールドが乗る
- README に「制約 / 既知の制限」セクション (Homestyler セレクター推測、model-viewer プレースホルダー等を明文化)

### Tests
- `tests/test_cancel.py` 7件: 404/409/JobManager 単体/パイプライン abort 2 ケース
- 計 **87 backend + 20 extension = 107 テスト**、カバレッジ **84%**

### Migrations
- 旧 jobs.db に `cancel_requested INTEGER DEFAULT 0` を ALTER TABLE で自動追加

## [0.5.0] - 2026-05-19

### Added
- レートリミット: トークンバケットで `/api/process` を IP ベース制限 (`RATE_LIMIT_BURST` / `RATE_LIMIT_PER_SEC`)
- `X-Forwarded-For` ヘッダの先頭値を IP として優先 (リバプロ対応)
- 多言語対応: `/api/errors/guidance` が `Accept-Language` ヘッダで日英切替
- 構造化ログ: `LOG_FORMAT=json` で 1行1JSON 出力に切替可能。extra フィールドも自動取込
- pytest-cov によるカバレッジ計測 (`fail_under=70`、現状 83%)
- CI に coverage アップロード追加
- ルート直下に `Justfile` (test/lint/fmt/serve/openapi など)
- `scripts/render_popup_screenshot.py` で README mockup を再生成可能

### Changed
- main.py が `services/logging_config.py` 経由でログ初期化
- conftest.py で各テスト前にレートリミットバケットを自動リセット

### Fixed
- ruff format `--check` の差分を全件解消

## [0.4.0] - 2026-05-19

### Added
- 構造化エラー: `ErrorCode` 列挙型と `PipelineError` を導入 (ADR-005)。`error_code` カラムを jobs に追加
- `GET /api/errors/guidance` でフロントエンド向けエラー対処辞書を公開
- `GET /api/jobs?limit=N` でジョブ履歴一覧 (created_at 降順)
- `EC3D_API_KEY` 環境変数による X-API-Key 認証ミドルウェア (未設定なら無効)
- Popup の 3 タブ UI: 「単発」「一括」「履歴」
- 一括投入: 複数 URL を行区切り入力し、バックグラウンドタブで順次スクレイプ
- 履歴タブ: `/api/jobs` を表示、リアルタイム再読込
- 3Dプレビュー枠: 完了時に `<model-viewer>` で GLB 表示 (model-viewer.min.js は別途同梱要)
- バックエンド `/output/*` 静的配信 (プレビュー用)
- ADR-001 〜 ADR-005 と CHANGELOG を `docs/` 配下に追加

### Changed
- `ProductData` を Pydantic で厳格バリデーション (HttpUrl、寸法0〜1000cm、画像 1〜50枚)
- 全パイプラインエラーを `PipelineError(code, message)` に統一

### Fixed
- `extractProductData` が商品名に含まれるカラー名を拾えるよう改善

## [0.3.0] - 2026-05-15

### Added
- SQLite による Job 永続化 (ADR-002)
- HTTP リトライ + 指数バックオフ (`services/http_retry.py`)
- Playwright 起動を `asyncio.Semaphore(1)` で直列化
- 画像 SHA-256 ハッシュキャッシュ (同じ画像で Tripo API を再呼び出ししない)
- 対応 EC サイト追加: low-ya.com / cainz.com / otsuka-kagu.co.jp
- pre-commit + ruff + prettier 設定
- Docker Compose: backend image (Python 3.11 + Blender + Playwright Chromium)
- SVG アイコン (等角投影の家具シルエット)
- CI: `lint-backend` ジョブ

### Changed
- 全 Python ファイルを ruff フォーマット適用

## [0.2.0] - 2026-05-15

### Added
- `/health/detail` で依存コンポーネント (Blender / API key / 認証情報) の状態を返却
- `output/` 起動時クリーンアップ (7日以上経過したファイルを削除)
- popup 進捗バー (step_index / total_steps を視覚化)
- ジョブの非同期化: `POST /api/process` が 202 + job_id を返し、popup が `/api/status/:id` を 1.5s ポーリング
- 拡張機能アイコン (16/48/128 PNG)
- E2E スクレイパーテスト (jsdom + ニトリ/IKEA/Amazon fixture)
- GitHub Actions CI: pytest + node --test + manifest.json lint

### Changed
- TRELLIS 2 ルートを削除し Tripo (fal.ai) 一本化 (ADR-001)
- CORS を `chrome-extension://` と `localhost` のみ許可する regex に変更 (ADR-003)
- FastAPI `@on_event` → `lifespan` に移行

### Fixed
- `parseDimensions` regex が "Width" 末尾の "h" を Height regex に誤マッチして 800mm を 80cm として拾うバグ
- JSDOM 互換のため `innerText` → `textContent` フォールバック

## [0.1.0] - 2026-05-14

### Added
- 初版: バックエンド (FastAPI) + Chrome 拡張機能 MVP
- 4ステップパイプライン: 画像DL → 3D生成 → スケール補正 → Homestyler アップロード
- 対応 EC サイト: ニトリ・IKEA・MUJI・Amazon JP・楽天
- Blender CLI による実寸スケール補正
- Playwright による Homestyler 自動アップロード
- 14 テスト (バックエンド) + 12 テスト (拡張機能)
