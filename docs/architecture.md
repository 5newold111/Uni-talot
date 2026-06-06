# アーキテクチャ

## 全体像

```
                          ┌─────────────────────────────┐
                          │      GitHub Actions (cron)    │  ← サーバーレス・無料枠
                          │  daily / 1日・15日トリガー    │
                          └───────────────┬─────────────┘
                                          │
                ┌─────────────────────────┼──────────────────────────┐
                │ 毎日 (daily-generation)  │  1日・15日 (album-release)│
                ▼                          ▼                           ▼
   ┌────────────────────┐    ┌────────────────────┐    ┌─────────────────────┐
   │ 1. トレンド分析     │    │ 4. アルバム集約     │    │ 5. 配信パッケージ生成 │
   │  Gemini API        │    │  前回リリース以降の  │    │  DistroKid 向け      │
   │  → TrendProfile    │    │  曲をまとめる        │    │  CSV + 音源 + カバー  │
   └─────────┬──────────┘    └─────────┬──────────┘    └──────────┬──────────┘
             ▼                         ▼                          ▼
   ┌────────────────────┐    ┌────────────────────┐    ┌─────────────────────┐
   │ 2. ブリーフ生成     │    │  カバーアート生成   │    │ 6. 通知（半自動）     │
   │  Gemini API        │    │  cover_art module  │    │  「UPして」と人へ通知 │
   │  → CreativeBrief×3 │    └────────────────────┘    └─────────────────────┘
   └─────────┬──────────┘
             ▼
   ┌────────────────────┐
   │ 3. 楽曲生成         │
   │  SUNO 非公式 API    │
   │  → Track(音源)×3   │
   └────────────────────┘
```

## 処理フロー

### 日次 (`scripts/run_daily.py`)

1. **トレンド分析** (`trend_analysis.TrendAnalyzer`)
   公開されているジャンル人気・BPM 帯・ムード傾向などの統計的シグナルを
   Gemini に集約させ、`TrendProfile` を得る。**既存曲そのものは解析しない。**
2. **ブリーフ生成** (`trend_analysis.BriefGenerator`)
   `TrendProfile` から、その日の **3 件のオリジナル創作ブリーフ**
   (`CreativeBrief`：タイトル・ジャンル・ムード・BPM・キー・楽器構成・
   構成・テーマ・SUNO 用スタイル/歌詞プロンプト) を Gemini で生成。
3. **楽曲生成** (`generation.SunoClient`)
   各ブリーフを SUNO 非公式 API に投入し、生成完了をポーリングして
   音源をダウンロード。`Track` として保存。
4. 生成結果（メタデータ JSON）を `state/` に追記し、音源を `output/tracks/` に保存。

### リリース日 (`scripts/run_release.py`) — 毎月 1 日・15 日

5. **アルバム集約** (`album.AlbumAssembler`)
   前回リリース以降に生成済みの `Track` を集めて `Album` を構成。
6. **カバーアート生成** (`cover_art`)
7. **配信パッケージ生成** (`distribution.DistributionPackager`)
   DistroKid が要求する形式（音源 / 3000×3000 カバー / メタデータ CSV）に整形し、
   `output/releases/<release-id>/` に出力。
8. **通知** (`notify`)
   「DistroKid にアップロードしてください」と人へ通知（メール / ログ）。
   → 人が DistroKid 画面で最終アップロード（**半自動**）。

## モジュール構成

| モジュール | 役割 |
|------------|------|
| `config.py` | 設定読み込み（`config/config.yaml` + 環境変数） |
| `models.py` | データモデル（`TrendProfile` / `CreativeBrief` / `Track` / `Album`） |
| `trend_analysis.py` | Gemini によるトレンド分析・ブリーフ生成 |
| `generation.py` | SUNO 非公式 API クライアント（楽曲生成） |
| `cover_art.py` | カバーアート生成（プラガブル） |
| `metadata.py` | DistroKid 向けメタデータ / CSV 生成 |
| `album.py` | アルバム集約 |
| `distribution.py` | 配信パッケージ化・半自動配信 |
| `storage.py` | 状態（生成済みトラック・最終リリース日）の永続化 |
| `notify.py` | 通知 |
| `pipeline.py` | 日次 / リリースのオーケストレーション |

## モックモード

`MUSIC_PIPELINE_MOCK=1`（または API キー未設定）の場合、外部 API を呼ばずに
決定論的なダミー出力を生成します。CI・開発・動作確認用です。実運用では各 API キーを
設定すると自動的に実モードへ切り替わります。

## コスト試算（月額・概算）

| 項目 | 費用 |
|------|------|
| GitHub Actions | 無料枠内（パブリックリポジトリは無制限） |
| Gemini API | 無料枠内（Flash 系の無料ティア） |
| SUNO サブスク | 約 $8〜10 |
| DistroKid | 約 $1.7（$19.99/年 ÷ 12） |
| **合計** | **約 $10〜12 / 月** |

## 拡張ポイント

- **カバーアート**: `cover_art.CoverArtGenerator` を画像生成 API（Gemini 画像 /
  Stable Diffusion 等）実装に差し替え可能。
- **配信**: 将来 API 対応ディストリビューター（Revelator / SonoSuite 等）へ移行する
  場合は `distribution.py` にアダプタを追加。
- **生成エンジン**: `generation.py` のインターフェースを実装すれば Udio 等へ差し替え可能。
