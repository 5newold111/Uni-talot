# ADR-006: 3D 生成プロバイダーをプラグイン化

- ステータス: 採用
- 日付: 2026-05-22

## 背景

ADR-001 で fal.ai Tripo 一本化したが、Tripo は有料 (1個 5〜50円)。月 50 個程度の個人利用でも月 250〜2500 円かかる。代替手段として:

- **TRELLIS (Microsoft, MIT ライセンス)** が Tripo 同等以上の品質
- Google Colab の T4 GPU 無料枠 (週 12〜15時間) で十分処理可能
- ngrok でローカル backend と接続すれば既存パイプラインは無改修で済む

「無料運用したい」「複数プロバイダーで品質比較したい」というニーズに応えるため、3D 生成を**プラグイン式**に抽象化する。

## 決定

- `services/model_providers.py` に抽象クラス `ModelProvider` を定義
  - `generate(image_path: str) -> bytes` のみ
- 環境変数 `MODEL_PROVIDER` で実装を切替:
  - `tripo` (default, 有料、既存)
  - `colab_trellis` (無料、要 Colab セットアップ)
  - `hf_space` (将来対応用スタブ)
- `services/model_generator.py` は SHA-256 キャッシュとファクトリー呼び出しのみ
- Colab ホスト用 notebook (`docs/trellis_colab.ipynb`) を同梱

## 結果

### 利点
- ユーザーは `.env` の 2 行変更で無料 (colab_trellis) ⇄ 有料 (tripo) を切替可能
- Tripo 解約しても品質は落ちない (TRELLIS は研究指標で Tripo 上回り)
- プロバイダー追加が容易 (`ModelProvider` を継承するだけ)
- 既存テストは互換性維持 (FAL_KEY モジュール変数を残した)

### トレードオフ
- Colab セッションが 12 時間で切れる → 週 1 回ノートブック再実行が必要
- ngrok 無料枠の URL はランダム → 切れる度に `.env` を更新する手間
- HF Space を直接叩く API はモデルごとに違うので `hf_space` は未実装で残した

### 失敗時の挙動
- Colab 未起動 / URL 失効: 502/503 を検出して「Colab セッションを再起動して新 URL を `.env` に反映」とエラーメッセージで明示
- プロバイダー間でエラーコード共通: `ErrorCode.MODEL_GENERATION_FAILED` / `MODEL_QUOTA_EXCEEDED` / `MODEL_API_KEY_MISSING`

## 代替案

| 案 | 採用しなかった理由 |
|---|---|
| バックエンド側で TRELLIS を直接動かす | GPU 必須、Docker イメージ巨大化、PC スペック要求が大幅増 |
| Replicate / Modal を強制 | 無料枠が小さい、ベンダー依存度が増す |
| HF Space を gradio_client で叩く | Space ごとに API 仕様が違い、`hf_space` プロバイダーをスタブで残した (将来必要なら個別実装) |

## 将来の拡張

- `hf_space` プロバイダーの実装 (gradio_client + Space ごとの API 仕様)
- Modal / Replicate プロバイダー (REST API ベース)
- 自動フォールバック (Tripo クォータ切れ → Colab に自動切替)
