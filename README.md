# 会計フリー帳 — 個人事業主向け 財務・会計管理システム

個人事業主（フリーランス）の **経費・売上の記帳**、**請求書（インボイス）発行**、
**青色申告（複式簿記）**、**消費税集計**、**税理士との共有**までを一気通貫で扱う
Web アプリケーションです。**データは Google スプレッドシート**に保存します。

> デモモード（インメモリ）でも動作し、Google 認証情報を設定すると
> そのままスプレッドシートをデータベースとして運用できます。

---

## 主な機能

| 機能 | 内容 |
| --- | --- |
| 認証・マルチユーザー | メール＋パスワードでのログイン／新規登録。データはユーザーごとに分離（セッションCookie） |
| ダッシュボード | 売上・経費・所得のサマリ、月次推移グラフ、経費内訳、最近の取引 |
| 取引・仕訳 | 経費／売上の**簡単入力**（自動仕訳）と、**詳細仕訳モード**（複式簿記・貸借バランス検証） |
| 領収書OCR | 領収書画像をブラウザ内でOCR（Tesseract.js）し、**金額・日付を自動入力**。画像も縮小して添付 |
| 請求書 | 適格請求書（インボイス）対応。税率区分ごとに消費税を集計。ステータス管理 |
| 取引先 | 得意先・仕入先の管理。インボイス登録番号を保持（仕入税額控除の判定に活用） |
| 勘定科目 | 個人事業主向け標準科目を同梱。事業に合わせて追加・編集可能 |
| 固定資産・減価償却 | **定額法／一括償却（3年）／少額特例（即時償却）**を自動計算。償却スケジュール表示 |
| レポート | 損益計算書（P/L）、貸借対照表（B/S）、消費税集計（本則課税ベースの概算） |
| 青色申告決算書 | 記帳データから**青色申告決算書（損益・貸借）**を自動組み替え。印刷/PDF・CSV出力 |
| 税理士共有 | 閲覧専用リンクの発行、仕訳帳の CSV エクスポート |
| 設定 | 事業者情報、申告方式（青色／白色）、消費税区分、青色申告特別控除額 |

> **デモアカウント**: `demo@example.com` / `demo1234`（サンプルデータ入り）

---

## 技術スタック

- **Next.js 14**（App Router） / **React 18** / **TypeScript**
- **Tailwind CSS**（UI）/ **Recharts**（グラフ）/ **lucide-react**（アイコン）
- **データストア**: Google スプレッドシート（`googleapis`）。認証情報が無い場合はインメモリにフォールバック
- **テスト**: Vitest（会計・税計算・集計ロジックのユニットテスト）

詳しい設計は [docs/DESIGN.md](docs/DESIGN.md) を参照してください。

---

## セットアップ

### 1. 依存関係のインストール

```bash
npm install
```

### 2. デモモードで起動（認証情報不要）

```bash
cp .env.example .env   # DATA_BACKEND=memory のままでOK
npm run dev
```

`http://localhost:3000` を開き、デモアカウント（`demo@example.com` / `demo1234`）でログインするか、
新規登録してお試しください。`.env` の `AUTH_SECRET` は本番では必ずランダム値に変更してください
（`openssl rand -base64 32`）。

### 3. Google スプレッドシート連携（本番）

詳細は [docs/GOOGLE_SHEETS_SETUP.md](docs/GOOGLE_SHEETS_SETUP.md) を参照。要点のみ:

1. Google Cloud でサービスアカウントを作成し **Google Sheets API** を有効化
2. サービスアカウントの鍵（JSON）から `client_email` と `private_key` を取得
3. `.env` に設定

   ```env
   DATA_BACKEND=sheets
   GOOGLE_SERVICE_ACCOUNT_EMAIL=xxxx@xxxx.iam.gserviceaccount.com
   GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   GOOGLE_SHEETS_SPREADSHEET_ID=   # 空でもOK（次のコマンドで作成）
   ```

4. スプレッドシートを作成し、タブ・初期勘定科目を投入

   ```bash
   npm run sheets:setup
   ```

   表示された `GOOGLE_SHEETS_SPREADSHEET_ID` を `.env` に設定し、
   作成されたスプレッドシートを自分（および税理士）の Google アカウントに共有します。

5. 起動

   ```bash
   npm run dev
   ```

---

## スクリプト

| コマンド | 説明 |
| --- | --- |
| `npm run dev` | 開発サーバー起動 |
| `npm run build` | 本番ビルド |
| `npm run start` | 本番サーバー起動 |
| `npm test` | ユニットテスト実行 |
| `npm run sheets:setup` | Google スプレッドシートの作成・初期化 |

---

## データ構造（スプレッドシートのタブ）

`Users` / `Accounts` / `Partners` / `Transactions` / `JournalLines` /
`Invoices` / `InvoiceItems` / `Attachments` / `FixedAssets` / `ShareLinks`

各タブの 1 行目がヘッダ（フィールド名）、2 行目以降が 1 レコードです。
金額はすべて **日本円の整数**で保持します。

---

## 注意事項

- 消費税の納付見込などは**概算**です。実際の申告は事業区分・控除要件・簡易課税の
  みなし仕入率等により異なります。確定申告時は税理士にご確認ください。
- 本 MVP は単一事業主を前提としています（マルチユーザー認証は今後の拡張ポイント）。
