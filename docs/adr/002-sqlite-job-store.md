# ADR-002: Job ストアを SQLite で永続化

- ステータス: 採用
- 日付: 2026-05-15

## 背景

初期実装ではジョブ状態を Python の dict にインメモリ保存していた。これは:

- サーバー再起動でジョブ履歴が全消失
- 拡張機能側からジョブ履歴 API を提供できない
- 同時実行中のジョブが失われると追跡不能

という問題があった。永続化が必要だが、Postgres を立てるのは家具EC個人プロジェクトとしてはオーバースペック。

## 決定

- 標準ライブラリの `sqlite3` で永続化
- スキーマ: `jobs (id, product_name, status, step, step_index, total_steps, message, result, error, error_code, created_at, updated_at)`
- DB パスは `JOB_DB_PATH` env で切替 (default: `./jobs.db`、Docker では `/data/jobs.db`)
- 7日経過したジョブは create 時に GC
- 同期 sqlite3 を `asyncio.to_thread` でラップしてイベントループをブロックしない

## 結果

**利点:**
- 外部依存ゼロ (Python標準)
- 軽量、シングルファイルでバックアップ容易
- WAL モードで読み書き並列性も担保

**トレードオフ:**
- 単一マシン限定 (複数サーバーで共有する場合は使えない)
- 大量ジョブには不向き (が、この用途では問題なし)
- マイグレーション機構が手動 (`ALTER TABLE IF NOT EXISTS` 相当が無いため手動チェック)

## 代替案

1. **Redis**: 高速だが永続化設定が複雑、別プロセス必要
2. **Postgres**: スケールするが運用コスト高
3. **DuckDB**: 分析向きでジョブ管理用途には機能過剰
4. **TinyDB (JSON)**: 排他制御が弱い、検索遅い

将来複数マシンで動かす場合は Postgres に移行 (ADR-XXX で別途)。スキーマは互換性を保てる。
