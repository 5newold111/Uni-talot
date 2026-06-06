# AI Music Pipeline 🎵

Gemini でトレンドを分析 → 創作ブリーフを生成 → **SUNO AI** で作曲 → アルバムとして
パッケージ化し、**DistroKid** 経由で各音楽プラットフォーム（Spotify / Apple Music /
YouTube Music など）へ配信する、**ローコスト・半自動**の楽曲制作パイプラインです。

> リポジトリ名は `furniture-3D-modeling-` ですが、中身は音楽生成・配信システムです
> （ブランチ `claude/music-generation-distribution-*` の作業）。

## できること

- **毎日 3 曲**を自動生成（GitHub Actions の cron で起動、サーバー不要）
- **毎月 1 日・15 日**に、それまで生成した曲を **アルバム**として自動パッケージ化
- 著作権セーフな **トレンド/メタデータ分析**（既存曲そのものは解析しない）
- API キーが無くても **モックモード**でパイプライン全体が動作（動作確認・開発用）

## 設計方針（重要）

| 工程 | 採用技術 | コスト | 備考 |
|------|----------|--------|------|
| スケジューラ | GitHub Actions (cron) | 無料枠 | サーバーレス |
| トレンド分析・作詞作曲ブリーフ | Gemini API | 無料枠あり | 著作権セーフな抽象化 |
| 楽曲生成 | SUNO（非公式 API） | ~$8-10/月 | サブスク必要 |
| カバーアート | Pillow で 3000×3000 PNG（無ければSVG） | 無料 | 画像生成APIに差し替え可 |
| 配信 | DistroKid（**半自動**） | ~$20/年 | 公式 API なし→最終UPのみ手動 |

### なぜ「半自動」配信なのか

DistroKid は**公式のアップロード API を提供していません**。本システムは配信に必要な
成果物（音源・カバー画像・メタデータ CSV）を**完全自動で生成・パッケージ化**し、
最後の「DistroKid 画面でのアップロード」だけを人手で行います。これが最も低コスト・
低リスク・利用規約に抵触しない方法です。詳細は [`docs/architecture.md`](docs/architecture.md)。

### 著作権への配慮

既存の楽曲（音源・歌詞・メロディ）そのものを解析・抽出して再生産することは**しません**。
公開されている**トレンドやメタデータ（ジャンル人気・BPM 帯・ムード傾向など統計的特徴）**
のみを抽出し、そこから**オリジナルの**創作ブリーフを生成します。詳細は
[`docs/legal-compliance.md`](docs/legal-compliance.md)。

## クイックスタート

```bash
# 1. 依存をインストール
pip install -r requirements.txt

# 2. （任意）API キーを設定。未設定ならモックモードで動きます
cp .env.example .env
# .env を編集

# 3. 1 日分（3 曲）を生成（モックモードならキー不要）
python scripts/run_daily.py

# 4. アルバムとしてパッケージ化（配信用成果物を出力）
python scripts/run_release.py --force
```

出力は `output/` 配下（曲・カバー・メタデータ・配信パッケージ）に生成されます。

## 開発

```bash
make install   # 依存インストール
make test      # pytest（モックモード）
make daily     # 3曲生成（モック）
make release   # アルバムパッケージ化（モック）
make clean     # 生成物を削除
```

CI（`.github/workflows/test.yml`）が push / PR でテストとスモークテストを実行します。

## ドキュメント

- [`docs/architecture.md`](docs/architecture.md) — 全体アーキテクチャと処理フロー
- [`docs/legal-compliance.md`](docs/legal-compliance.md) — 著作権セーフな分析方針
- [`docs/setup.md`](docs/setup.md) — API キー取得・GitHub Actions 設定手順

## ライセンス

MIT
