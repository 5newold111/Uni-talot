# Architecture Decision Records (ADR)

このプロジェクトで採用したアーキテクチャ上の意思決定の記録。

| # | タイトル | ステータス | 日付 |
|---|---------|-----------|------|
| [001](./001-drop-trellis-for-tripo.md) | TRELLIS 2 を採用見送り、Tripo (fal.ai) 一本化 | 採用 | 2026-05-15 |
| [002](./002-sqlite-job-store.md) | Job ストアを SQLite で永続化 | 採用 | 2026-05-15 |
| [003](./003-cors-regex-policy.md) | CORS は chrome-extension と localhost のみ regex 許可 | 採用 | 2026-05-15 |
| [004](./004-homestyler-playwright-bot.md) | Homestyler 連携は Playwright ボット (公式API無し) | 採用 (要保守) | 2026-05-15 |
| [005](./005-structured-error-codes.md) | パイプラインエラーは ErrorCode 列挙型で構造化 | 採用 | 2026-05-19 |

## ADR の書き方

新しい意思決定があったら `XXX-short-title.md` を作成して以下のテンプレートで記述:

```markdown
# ADR-XXX: タイトル

- ステータス: 検討中 | 採用 | 廃止 | 上書き (ADR-YYY)
- 日付: YYYY-MM-DD

## 背景
解決すべき問題、制約、関連する事実

## 決定
何を採用したか

## 結果
採用したことで得られる利点、許容するトレードオフ

## 代替案
検討したが採用しなかった選択肢と理由
```
