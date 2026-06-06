# セットアップ手順

## 1. ローカル開発

```bash
git clone <repo>
cd furniture-3D-modeling-
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 任意。未設定ならモックモードで動作
```

### モックモードで動作確認

API キーが無くても、パイプライン全体がダミー出力で動きます。

```bash
python scripts/run_daily.py            # 3曲ぶんのブリーフ+ダミー音源を生成
python scripts/run_release.py --force  # アルバムをパッケージ化
ls -R output/
```

## 2. API キーの取得

| 変数 | 取得先 | 必須 | 備考 |
|------|--------|------|------|
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey | 実モードで必須 | 無料枠あり |
| `SUNO_API_KEY` / `SUNO_BASE_URL` | SUNO 非公式 API ラッパー | 楽曲生成で必須 | 下記参照 |
| `NOTIFY_EMAIL` | 任意 | 任意 | 通知先メール |

`.env` に設定すると、対応工程が自動的に実モードへ切り替わります。
特定工程だけモックにしたい場合は `MUSIC_PIPELINE_MOCK=1` で全体をモック化できます。

### SUNO 非公式 API について

SUNO は公式 API を一般提供していないため、コミュニティ製のラッパー
（自己ホスト型のプロキシ等）を利用します。`SUNO_BASE_URL` にそのエンドポイントを、
`SUNO_API_KEY` に認証情報を設定してください。`src/music_pipeline/generation.py` の
`SunoClient` は一般的な「生成リクエスト → ポーリング → 音源 URL 取得」フローを
想定していますが、利用するラッパーの仕様に合わせてエンドポイント名の調整が必要です。

> 非公式 API は仕様変更リスクがあります。利用は SUNO の規約の範囲内で行ってください。

## 3. GitHub Actions（自動運用）

### Secrets を登録

リポジトリの **Settings → Secrets and variables → Actions** に以下を登録：

- `GEMINI_API_KEY`
- `SUNO_API_KEY`
- `SUNO_BASE_URL`
- （任意）`NOTIFY_EMAIL`, `SMTP_*`

### ワークフロー

- `.github/workflows/daily-generation.yml`
  毎日 cron 起動 → 3 曲生成 → メタデータを `state/` にコミット、音源をアーティファクト化。
- `.github/workflows/album-release.yml`
  毎月 1 日・15 日に起動 → アルバムをパッケージ化 → GitHub Release として成果物を添付し通知。

cron の時刻は UTC です。JST に合わせる場合は `-9h` してください
（例: JST 09:00 = UTC 00:00 → `0 0 * * *`）。

## 4. 配信（半自動の最終ステップ）

1. リリース実行後、`output/releases/<release-id>/` に配信パッケージが生成されます。
   - `tracks/` … 音源ファイル
   - `cover.*` … カバーアート
   - `distrokid_metadata.csv` … トラック情報一覧
   - `UPLOAD_INSTRUCTIONS.md` … アップロード手順
2. 通知（メール/ログ）に従い、DistroKid にログインしてアップロードします。
3. 各ストア（Spotify / Apple Music / YouTube Music 等）へ DistroKid が配信します。

## トラブルシュート

- **`google-generativeai` が無い**: 実モードのみ必要。`pip install -r requirements.txt`。
- **SUNO がタイムアウト**: `SUNO_POLL_TIMEOUT` を延ばす。ラッパーの稼働を確認。
- **全部モックになる**: キー未設定か `MUSIC_PIPELINE_MOCK=1` を確認。
