# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.4.0] - 2026-05-24

### Added — Chrome 拡張機能なしで使えるスタンドアロン Web UI
- `backend/ui/index.html`: ブラウザで `http://localhost:3000/ui/` を開いて
  URL を貼り付けて使えるスタンドアロン UI (拡張機能インストール不要)
  - 単発 URL タブ: URL 入力 + 寸法手動上書き + 3D プレビュー
  - 一括 URL タブ: 行区切り URL を順次投入
  - 履歴タブ: `/api/jobs` を表示
  - 使い方タブ: 制約とサンプル curl コマンドを記載
- `backend/services/url_scraper.py`: サーバー側 HTML スクレイパー
  - og:image / og:title / h1 / title の優先順で商品名抽出
  - og:image を front 画像に、追加 img タグから 4 件を other に
  - 寸法は `W×D×H` パターン / `数×数×数 mm|cm` パターンを正規表現抽出
  - 相対 URL を絶対 URL に正規化 (`//cdn/x.jpg`, `/img/x.jpg` 両対応)
  - SSRF 防御 (`is_url_safe()` で内部 IP 弾き)
- `POST /api/process-url`: URL 1 件を受け取りサーバー側で抽出 → 投入
  - 寸法をクライアント側で上書き指定可能
  - 画像が 1 枚も取れなかったら 422 で「拡張機能版を試してください」
- `main.py` で `/ui/` 静的マウント追加

### Tests (20 新規)
- `_parse_dimensions` の WxDxH / triple x / 該当なし
- `_absolute_url` の絶対 / プロトコル相対 / ルート相対 / 相対
- `scrape_product_url`: og タグ抽出 / H1 フォールバック / 寸法抽出 / 404 / SSRF 拒否 / javascript: 拒否
- `/api/process-url` エンドポイント: success / dimensions 上書き / 画像なし 422 / 不正 URL 422
- `/ui/` 静的配信: index.html が返る / URL 入力欄が含まれる

### Limitations (率直に)
- JS でレンダリングされる SPA 商品ページは取れない (HTML 直読みなので)
- 拡張機能版に比べて寸法抽出精度が低い (個別セレクタ未対応)
- 詳細な情報が必要なら依然として Chrome 拡張機能版が推奨

### Numbers
- backend tests: 168 → 188 (+20)
- 合計テスト: 214 → 234
- エンドポイント: 8 → 9
- カバレッジ: 93.1%

## [2.3.0] - 2026-05-22

### Added — 拡張機能で任意の URL を直接入力可能に
- 単発タブに**ソースモード切替ラジオ** (`active` / `url`) を追加
  - `active` (default): 開いているタブから商品情報を抽出 (既存挙動)
  - `url`: 入力欄に貼った URL をバックグラウンドタブで開いて抽出 → 自動でタブを閉じる
- URL 入力欄にリアルタイム検証:
  - 形式不正 (`javascript:` 等) → 赤枠 + エラー文
  - 対応 EC サイト → 「✓ 対応サイト」(緑)
  - 対応外サイト → 「default セレクター頼みになります」(黄)
- 共通ヘルパー `scrapeFromUrl(url)` を popup.js に追加。単発タブ URL モードと一括投入で共有
- `popup_utils.js` に `isValidProductUrl()` / `isSupportedEcSite()` を追加 (テスト容易化)

### Tests (16 新規)
- `isValidProductUrl`: 有効/空白/非 http スキーム/ホスト名なし/trim の 5 ケース
- `isSupportedEcSite`: 全 8 対応サイト/サブドメイン/対応外/不正 URL の 4 ケース

### UX 改善
- 「現在のタブ」モードは既存ユーザーの体験を維持 (デフォルト動作)
- URL モードは「ブラウザで開かずに 1 件だけ処理したい」「Slack で送られた URL を直接処理したい」用途に対応
- 入力ミス時はバックエンドに送る前に検出 → クレジット浪費防止

### Metrics
- extension テスト: 37 → 46 (+9)
- 合計テスト: 205 → **214**

## [2.2.0] - 2026-05-22

### Added — 完全無料運用パスを実装 (ADR-006)
- **ModelProvider 抽象化**: `services/model_providers.py` に 3 プロバイダー
  - `tripo` (default, 有料、既存実装)
  - `colab_trellis` (**完全無料**、Google Colab で TRELLIS をホスト)
  - `hf_space` (スタブ、将来拡張)
- 環境変数 `MODEL_PROVIDER` で切替。`MODEL_PROVIDER=colab_trellis` + `TRELLIS_COLAB_URL=https://xxx.ngrok-free.app` の 2 行で**完全無料運用**に切替可能
- `docs/trellis_colab.ipynb`: Google Colab T4 GPU で TRELLIS を起動 + ngrok でトンネル
  公開する notebook。週 1 回起動するだけで月 50 個以上の 3D 生成が完全無料
- `services/model_generator.py` を抽象に委譲する形に書き換え。SHA-256 キャッシュは
  どのプロバイダーでも有効

### Tests (14 新規)
- ファクトリーが MODEL_PROVIDER env で正しいクラスを返す (default / colab / 未知)
- プロバイダー認証/URL 未設定の早期検出
- ColabTrellisProvider が multipart で画像送信し GLB バイナリを受け取る
- ngrok/Colab セッション切れ (502/503/404) を明示メッセージで検出
- generate_3d_model のキャッシュがプロバイダー呼び出しを抑止

### Docs
- ADR-006: 3D 生成プロバイダーをプラグイン化
- README に「無料運用パス (Colab + TRELLIS)」セクション (次回更新で追記予定)

### Numbers
- backend テスト: 154 → 168 (+14)
- カバレッジ: 93.07% → 93.11%
- 環境変数: 17 → 19 (`MODEL_PROVIDER`, `TRELLIS_COLAB_URL`)

### Migration
- 既存ユーザーはコード変更不要。`MODEL_PROVIDER` を設定しなければ tripo がデフォルトで動く
- 無料化したい場合: docs/trellis_colab.ipynb を Colab で起動 → 表示された URL を .env に貼る

## [2.1.0] - 2026-05-22

### Added
- Homestyler 実画面の組み込みツール群:
  - `scripts/calibrate_homestyler.py` CLI に 4 サブコマンド:
    - `login` — ブラウザを立ち上げ手動ログイン → `homestyler_storage_state.json` に
      Playwright storage_state を保存 (CAPTCHA / Google OAuth 通過可)
    - `probe` — 既定セレクターが現在の画面で可視か全件チェック (UI 変更検出)
    - `capture <name>` — DevTools で取得したセレクターを実画面で検証して
      `homestyler_selectors.json` に保存
    - `dump-dom` — 現在画面の HTML/PNG/URL を logs/ に保存
- `services.homestyler_bot` の認証ロジックを書き換え:
  - `homestyler_storage_state.json` があればセッション復元 (login 画面を完全スキップ)
  - なければ email/password でフォールバック自動ログイン
  - storage_state でアクセス後 login/signin URL に飛ばされたら失効として即座に検出
- `homestyler_selectors.json` による外部セレクター上書き
  (コード変更なしで実画面のセレクターに差し替え可能)
- 失敗時の自動デバッグダンプ: `logs/error_<product>_<ts>.{png,html,url.txt}`
- 早期認証チェック: storage_state も email/password も無ければ Chromium 起動前に失敗
- `ec3d_cli.py calibrate <subcommand>` 統合: 単一の CLI から calibrate も呼び出せる
- `HOMESTYLER_HEADLESS=false` / `HOMESTYLER_SLOW_MO=<ms>` env 対応 (デバッグ用)
- `HOMESTYLER_STORAGE_STATE` / `HOMESTYLER_SELECTORS` env でパス変更可

### Tests
- `tests/test_homestyler_calibration.py` 11件:
  - _load_selectors の default / override / 不正 JSON
  - _have_storage_state の missing / empty / present
  - upload が storage_state を context に渡す検証
  - storage_state なしのフォールバック
  - セレクター上書きが実 upload で使われる
  - 失効セッション検出 (HOMESTYLER_AUTH_FAILED)
  - 失敗時の DOM/PNG/URL ダンプ

### Metrics
- backend テスト: 125 → **136** (+11)
- カバレッジ: 86.45% → ~93%

### Limitations (率直に明記)
- このサンドボックスからは homestyler.com に到達できない (HTTP 403)。
  実画面操作の検証はユーザー側ローカル環境で `calibrate login` を実行することで完了する。
- 全ての code path はテストで検証済み (Playwright をモックしてセッション復元 /
  失効検出 / セレクター上書き / ダンプ生成を確認)。

## [2.0.0] - 2026-05-22

### Breaking
- **コアパイプラインから Homestyler アップロードを分離**。
  `POST /api/process` のパイプラインは 4 ステップ → **3 ステップ** (download → generate → scale) になった。
  Homestyler に GLB を流すには `POST /api/jobs/{id}/upload-to-homestyler` を別途呼ぶ。
  STEPS 配列も短くなったので `total_steps` は新規ジョブで 3 を返す (旧ジョブは 4 のまま)。

### Why (根本的な見直し)
- Homestyler セレクターは推測値で本番動作未検証。それが全ジョブの必須パスにあったため、
  Tripo に課金して GLB を生成してもジョブ全体が "error" 状態になり、ユーザーは何も
  手にできなかった。これは課金がある以上、設計として誤り。
- 新設計では:
  - Tripo クレジットを消費して生成した GLB は確実に手元に残る (`result.glb`)
  - Homestyler が壊れていてもコアジョブの `success` 状態は維持される
  - Homestyler はオプショナルな後処理として明示的に呼ぶ (副作用の透明化)
  - GLB は `/output/<file>` で直接ダウンロード可能 (Homestyler を使わない用途にも対応)

### Added
- `POST /api/jobs/{job_id}/upload-to-homestyler` エンドポイント:
  成功ジョブの保存済み result からアップロードを起動。Homestyler が失敗しても
  `result.glb` は保持されるので無限に再試行できる。
- ジョブ result に `dimensions`/`category`/`source_url` を保存 (Homestyler 後処理で必要)
- `backend/scripts/ec3d_cli.py`: CLI ツール (`ec3d submit/status/watch/jobs/cancel/upload-homestyler`)。
  EC3D_API_URL / EC3D_API_KEY 環境変数で認証ヘッダも自動付与。
  cron / シェルスクリプト / CI からの自動化に対応。
- popup に「Homestylerにアップロード (任意)」ボタンを追加。3D 生成成功後にのみ表示。

### Tests
- `tests/test_homestyler_endpoint.py` 5件: 404/409/result 使用/失敗時 GLB 保持/コア無干渉
- `tests/test_cli.py` 11件: submit/status/watch/jobs/cancel/upload-homestyler の各分岐

### Metrics
- backend テスト: 109 → **125** (+16)
- 合計テスト: 146 → **162**
- カバレッジ: 86% → **86.45%**

### Migration guide
旧 1.x クライアントがある場合の対応:
- ジョブの `total_steps` が 4 → 3 に変わる (新規ジョブのみ)
- ジョブ完了時の `step` が `done` で、自動的に Homestyler に上がらない
- Homestyler に流したい場合は: `curl -X POST /api/jobs/<id>/upload-to-homestyler`

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
