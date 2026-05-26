# ADR-005: パイプラインエラーは ErrorCode 列挙型で構造化

- ステータス: 採用
- 日付: 2026-05-19

## 背景

初期実装は `RuntimeError("HF API ...")` や `RuntimeError("Blender ...")` のように文字列をそのままジョブの error フィールドに格納していた。これだと:

- フロントエンドが「APIクォータ切れ」と「Homestyler UI壊れた」を区別できない
- 復旧手順を画面に出せない (全部「サーバーエラー」になる)
- ログ検索でエラーカテゴリ別集計ができない
- 多言語化が困難 (メッセージが日本語ハードコード)

## 決定

- `services/errors.py` に `ErrorCode` Enum を定義 (11種類)
- 全パイプライン例外を `PipelineError(code, message)` で投げる
- `jobs` テーブルに `error_code TEXT` カラムを追加 (`ALTER TABLE` で既存DBもマイグレーション)
- `services/errors.py` の `USER_GUIDANCE` 辞書で error_code → ユーザー向け対処メッセージを保持
- 新 API `GET /api/errors/guidance` で辞書をクライアントに公開
- popup は失敗時 `error_code` を見てガイダンスを表示

## 結果

**利点:**
- popup で「FAL_API_KEY 未設定だから `.env` を確認」のような行動可能なメッセージが出る
- ログを `grep error_code=model_quota_exceeded` で集計可能
- 多言語化は USER_GUIDANCE 辞書を翻訳するだけ
- API クライアント (cron など) もエラーカテゴリで分岐可能

**トレードオフ:**
- エラー追加時は ErrorCode + USER_GUIDANCE + 投げる箇所の 3 か所更新
- 既存テストの `RuntimeError` 期待を `PipelineError` に書き換える必要があった

## 代替案

1. **HTTP ステータスコードに集約**: ジョブ実行中のエラーをHTTPで表せない (常に 200 + job.status="error")。
2. **logger に構造化フィールドだけ載せる**: フロントエンドは触れない。
3. **OpenTelemetry を導入して集約**: オーバースペック。
