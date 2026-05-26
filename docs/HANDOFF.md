# EC3D-Bridge セッション引き継ぎノート

最終更新: 2026-05-26
ブランチ: `claude/ec3d-bridge-implementation-fv9ap`
直近: v2.5.1 (IKEA など SPA サイトでの FAB 表示不具合を修正)

---

## 1. 現状サマリ

v2.5 まで完了済み。動作する状態でブランチに push 済み。
ローカル CI 相当 (pytest / node --test / ruff / manifest 検証) は全部グリーン。

| バージョン | 主な変更 |
|----------|----------|
| v0.x → v1.0 | MVP 完成 (FastAPI + Chrome 拡張 + Tripo + Blender + Homestyler) |
| v1.0.x | Blender 4.0+ 対応 / カバレッジ強化 / セキュリティ監査 |
| v2.0 | Homestyler を本流から切り離し (失敗しても GLB は残る) |
| v2.1 | storage_state によるログイン情報の安全保管 / calibrate CLI |
| v2.2 | 3D 生成プロバイダーをプラグイン化 (Tripo / Colab TRELLIS / HF Space) |
| v2.3 | 拡張機能ポップアップに URL 入力モード |
| v2.4 | スタンドアロン Web UI (`http://localhost:3000/ui/`) |
| **v2.5** | EC ページ右下に「3D化」フローティングボタン (Shadow DOM) |

---

## 2. 未対応の最優先タスク

(現在なし — v2.5.1 で IKEA 対応完了)

---

## 2.5. 解決済みの履歴

### ✅ IKEA サイトで FAB がうまく表示されない (v2.5.1, 2026-05-26)

採用した解決策:
1. `looksLikeProductPage()` を SITE_CONFIGS.images セレクタ駆動に変更
   → ヘッダーロゴで誤発火しなくなり、SPA hydration 前なら observer 待機に流れる
2. `waitForProductPage()` で MutationObserver を最大 8 秒、debounce 300ms で再判定
3. `site_configs.js` IKEA セレクタを実 DOM (`pip-header-section__title__label`,
   `picture img.pip-image` 等) に追従
4. `test_floating_button.mjs` に IKEA スケルトン → hydration の回帰テスト 4 件
5. `test_url_scraper.py` に SODERHAMN URL fixture で `/api/process-url` E2E 検証

---

## 2-(旧). 元の不具合説明 (参考用)

### 🐛 IKEA サイトで FAB がうまく表示されない

ユーザー報告:
> 「IKEAのサイトにうめく表示されてません。」
> (「うめく」は「うまく」のタイポと判断)

#### 原因の仮説

`extension/content_scripts/floating_button.js:40-44` の `looksLikeProductPage()` が
原因の可能性が高い:

```js
function looksLikeProductPage() {
  const hasH1 = document.querySelectorAll(
    "h1, [class*='item_name'], [class*='product-name'], [data-testid='product-title']"
  ).length > 0;
  const hasManyImages = document.querySelectorAll("img").length >= 3;
  return hasH1 && hasManyImages;
}
```

`run_at: "document_idle"` のタイミングで以下が発生すると判定が外れる:

1. **IKEA は React SPA**: 初期 HTML はスケルトン、商品タイトル・画像は
   ハイドレーション後に挿入される。`document_idle` でも間に合わないケースあり。
2. **画像が lazy-load**: 初期 `<img>` の数が 3 未満になり閾値割れ。
3. **SPA 内ナビゲーション**: PDP → 別 PDP の遷移で content script が
   再実行されない (manifest content_scripts は初回ロードのみ)。

#### 推奨アプローチ (3 段構成)

1. **SITE_CONFIGS ヒット時は強い肯定シグナルとして扱う**
   `getSiteConfig(location.hostname).site !== "unknown"` なら h1/img 閾値は
   緩める (例: `images >= 1` または完全に省略)。

2. **MutationObserver で再判定 (タイムアウト付き)**
   `init()` でヒットしなかった場合、`document.body` に `childList: true,
   subtree: true` で observer を仕掛け、最大 8 秒間、500ms デバウンスで
   `looksLikeProductPage()` を再評価。ヒットしたら注入 + observer 解除。

3. **IKEA フィクスチャ回帰テスト追加**
   `extension/tests/test_floating_button.mjs` に
   - 初期 DOM は h1 なし → 後から `<h1 class="pip-header-section__title">`
     が追加される → 注入される
   - のシナリオを 1 ケース足す。

#### 触るべきファイル

| ファイル | 目的 |
|----------|------|
| `extension/content_scripts/floating_button.js` | 上記 1, 2 の実装 |
| `extension/tests/test_floating_button.mjs` | 上記 3 の回帰テスト |
| `extension/scrapers/site_configs.js` | 必要なら IKEA セレクタを微調整 |
| `CHANGELOG.md` | v2.5.1 として追記 |

#### 確認手段の制約

サンドボックスから ikea.com への実アクセスは 403 で落ちる。
JSDOM フィクスチャで「初期 → mutation で h1 追加」シナリオを検証するのが現実的。
ユーザー側で実 IKEA ページでの確認をお願いする想定。

---

## 3. 既知の前提・制約 (次セッションが踏まないように)

### セキュリティガードレール (絶対に外さない)

- `.env`, `homestyler_storage_state.json`, `logs/`, `output/` は **commit 禁止** (`.gitignore` 済)
- `SecretRedactor` (logging filter) は維持: `FAL_API_KEY` / `HOMESTYLER_PASSWORD` /
  `EC3D_API_KEY` / `HF_TOKEN` をマスク
- `url_safety.is_url_safe()` を経由しない外部 URL fetch は追加禁止 (SSRF 防御)
- CORS regex は `chrome-extension://` と `localhost` のみ。`*` は付けない
- `EC3D_API_KEY` 未設定時は無認証 (個人ローカル想定)。本番化する人は要設定

### Blender

- 4.0+ 必須。`export_selected` は撤去済 (`use_selection` を使う)
- `backend/services/scale_correction.py` のテストは実 Blender が無いと skip

### 外部到達不能 (サンドボックス)

- fal.run / homestyler.com / huggingface.co / ikea.com いずれも 403
- Playwright Chromium のダウンロードも不可
- → ロジックは mock でテスト、実機検証はユーザー側

### 3D プロバイダー

- `MODEL_PROVIDER=tripo` (有料、デフォルト) / `colab` (無料・要 ngrok) / `hf_space`
- `backend/services/model_providers.py` に抽象化済み
- 月 50 個無料運用は `docs/trellis_colab.ipynb` の手順 (Colab + TRELLIS + ngrok)

---

## 4. すぐ動かすためのコマンド

```bash
# バックエンド開発サーバ
cd backend && uvicorn main:app --reload --port 3000

# 拡張機能をブラウザに読み込む
# chrome://extensions → デベロッパーモード ON → 「パッケージ化されていない拡張機能を読み込む」
# → extension/ を選択

# テスト一括 (Justfile が用意済)
just test            # backend pytest + extension node --test
just lint            # ruff + manifest 検証

# 単体
cd backend && pytest tests/ -v
cd extension && node --test tests/test_floating_button.mjs
```

---

## 5. ファイルマップ (要点だけ)

```
backend/
  main.py                          FastAPI エントリ + lifespan
  routers/process.py               /api/process /api/status /api/cancel
  services/
    model_providers.py             Tripo / Colab / HF Space
    scale_correction.py            Blender CLI ラッパ (cm スケール)
    homestyler_bot.py              Playwright で実画面操作
    url_safety.py                  SSRF 防御
    logging_setup.py               SecretRedactor + JSON ログ
  scripts/
    calibrate_homestyler.py        ログイン情報を storage_state.json に保存
    dump_openapi.py                docs/openapi.json 再生成 (CI ドリフト検知)

extension/
  manifest.json                    MV3, v2.5.0, 8 EC サイト対応
  content_scripts/
    scraper.js                     extractProductData() (window 公開済)
    floating_button.js             ⚠️ IKEA 対応で要更新
  scrapers/site_configs.js         サイト別セレクタ
  popup/                           ポップアップ UI (URL 入力 / 設定タブ含む)
  background/service_worker.js
  tests/                           jsdom + node --test

docs/
  trellis_colab.ipynb              Colab で無料 3D 生成
  openapi.json                     CI で drift 検知
  floating_button_screenshot.png   v2.5 UI スクショ
  HANDOFF.md                       ← このファイル
```

---

## 6. 次セッションへの依頼テンプレ

> IKEA サイトでフローティングボタン (FAB) が表示されない問題を
> `docs/HANDOFF.md` の「2. 未対応の最優先タスク」の方針 (SITE_CONFIGS ヒット時は
> 閾値緩和 + MutationObserver で SPA ハイドレーション待ち) で修正し、
> 回帰テストを追加して v2.5.1 として commit + push してください。
