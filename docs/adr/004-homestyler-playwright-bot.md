# ADR-004: Homestyler 連携は Playwright ボット (公式API無し)

- ステータス: 採用 (要保守)
- 日付: 2026-05-15

## 背景

Homestyler には公式の「マイモデル GLB アップロード」API が存在しない。商品登録ワークフローを自動化する手段は事実上以下に限られる:

1. ブラウザ自動操作 (Playwright / Puppeteer / Selenium)
2. リバースエンジニアリングした内部 API 直叩き (ToS 違反リスク)
3. 手動アップロード (現状の運用)

## 決定

- Playwright (async) で Chromium をヘッドレス起動
- メール+パスワードでログイン → マイモデル画面 → GLB アップロード
- セレクターは `SELECTORS` 定数にまとめて変更時の影響範囲を局所化
- 失敗時は DOM スクリーンショットを `logs/error_<product>.png` に保存

## 結果

**利点:**
- 公式手順の延長で「やってることは人間と同じ」
- セレクター更新だけで UI 変更に追従可能
- スクリーンショットでデバッグ容易

**トレードオフ (これが大きい):**
- Homestyler の UI 変更で即座に壊れる
- CAPTCHA / Google OAuth / BotGuard が入ると突破不可
- 1ジョブ毎に Chromium 起動 → 重い (Semaphore で直列化)
- IP ベース BAN のリスク

## 必須運用ガイドライン

1. **本番運用前に headless=False で目視キャリブレーション** (README の「Homestyler セレクター検証手順」参照)
2. **CAPTCHA が現れたら `storage_state()` ベースのセッション保持に切替**
3. **大量投入 (10+件/日) は NG** — レート制限と BAN リスク
4. **失敗が増えたらまずスクリーンショット確認**

## 代替案

1. **API リクエストの再現**: ChromeDevTools で発見した XHR/fetch をhttpx で再現。短期間動くが Cloudflare/CSRF トークン認証を突破する必要があり、保守不能。
2. **手動運用に戻す**: 1日数件なら手動が現実的。
3. **競合サービス (Sketchfab, 3D Warehouse) に切替**: Sketchfab は API ありの可能性。今後検討余地。

長期的には公式 API がないサービスへの依存自体がアーキテクチャ的負債であることを認識しておく。
