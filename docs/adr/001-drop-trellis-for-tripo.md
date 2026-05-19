# ADR-001: TRELLIS 2 を採用見送り、Tripo (fal.ai) 一本化

- ステータス: 採用
- 日付: 2026-05-15

## 背景

当初の設計では 3D 生成プロバイダーを 2 系統用意し、`USE_TRIPO` 環境変数で切替する想定だった:

- **Phase 1**: TRELLIS 2 (Microsoft) を HuggingFace Inference API 経由で呼び出し
- **Phase 2**: Tripo 2.5 (VAST AI) を fal.ai 経由で呼び出し

しかし、実装後の検証で `https://api-inference.huggingface.co/models/microsoft/TRELLIS-image-large` は HF Inference API では提供されていないことが判明した。TRELLIS は Gradio Space としてのみ公開されており、別途 Space の API を呼ぶ必要がある (認証・キュー・タイムアウト等が異なる)。

## 決定

- TRELLIS 2 ルートを完全削除
- `USE_TRIPO` 環境変数を廃止
- `HF_TOKEN` を `.env.example` から削除
- 3D 生成は Tripo 2.5 (fal.ai) のみとする

## 結果

**利点:**
- コード分岐が消えて単純化、テストすべきパスが半減
- 動かないコードが本番に残らない (誤情報を残さない)
- fal.ai の課金で予算を一元管理できる

**トレードオフ:**
- プロバイダー単一障害点になる (fal.ai がダウンしたら停止)
- ベンダーロックイン

## 代替案

1. **TRELLIS の Gradio Space API を実装**: HuggingFace Space は WebSocket または `/run/predict` 形式の独自 API を持つ。実装可能だが安定しておらず、レート制限が厳しい。
2. **Replicate / Modal で TRELLIS を自前ホスト**: コスト・運用負荷が大きい。
3. **複数プロバイダーをアダプターパターンで抽象化**: 将来必要になったら ADR を別途追加して導入する。

将来 TRELLIS が HF Inference に正式対応した場合は、この ADR を「上書き」する形で復活させる。
