# 設計書 — 会計フリー帳

## 1. 目的とスコープ

個人事業主が日々の **経費・売上を記帳**し、**請求書を発行**し、**青色申告**に必要な
帳簿（複式簿記）と **消費税集計**を行い、**税理士と共有**できる Web アプリ。

- 申告方式: 青色申告（複式簿記）を主、白色も選択可
- 消費税: 課税／免税事業者、本則／簡易課税、インボイス（適格請求書）対応
- データ保存: Google スプレッドシート（タブ＝テーブル）

## 2. アーキテクチャ

```
ブラウザ (React/Next App Router)
   │  Server Actions / Route Handlers
   ▼
リポジトリ層 (src/lib/repo.ts)  ── 会計ロジック (accounting.ts) / 集計 (reports.ts)
   │  Store 抽象 (src/lib/data/store.ts)
   ├── SheetsStore  → Google Sheets API（本番）
   └── MemoryStore  → プロセス内（デモ・テスト）
```

- **Store 抽象**により、データの実体（Sheets / メモリ）を差し替え可能。
  認証情報の有無で自動選択（`DATA_BACKEND` で明示も可能）。
- **会計・集計ロジックは純粋関数**としてストアから分離し、ユニットテスト可能。
- **認証**: メール＋パスワード（scrypt ハッシュ）と HMAC 署名付きセッションCookie。
  外部依存を増やさず `node:crypto` で実装（`src/lib/auth.ts`）。`(app)` レイアウトで
  未ログインを `/login` にリダイレクトし、リポジトリ層はセッションのユーザーに自動スコープ。

### ディレクトリ

```
src/
  app/
    (app)/            … サイドバー付きの本体画面（ルートグループ）
      page.tsx        … ダッシュボード
      transactions/   … 取引・仕訳（一覧/新規/編集）
      invoices/       … 請求書
      partners/       … 取引先
      accounts/       … 勘定科目
      reports/        … レポート（P/L・B/S・消費税）
      settings/       … 設定
      share/          … 税理士共有
    shared/[token]/   … 共有閲覧ビュー（サイドバー無し・外部向け）
    api/export/journal … 仕訳帳CSV
    actions.ts        … Server Actions（作成/更新/削除）
  components/         … UI コンポーネント
  lib/
    constants.ts      … 区分（勘定科目区分・税区分など）の唯一の正
    types.ts          … ドメイン型
    auth.ts/session.ts… 認証（パスワードハッシュ・セッションCookie）
    accounting.ts     … 消費税・貸借・残高ロジック（純粋関数）
    reports.ts        … P/L・B/S・消費税集計・月次（純粋関数）
    depreciation.ts   … 減価償却（定額法/一括/即時）（純粋関数）
    taxReturn.ts      … 青色申告決算書の組み替え（純粋関数）
    ocrParse.ts       … 領収書OCRテキストの金額・日付抽出（純粋関数）
    defaultAccounts.ts… 標準勘定科目テンプレート
    format.ts / csv.ts… 表示整形・CSV生成
    data/             … Store 抽象・Sheets/メモリ実装・スキーマ・シード
scripts/setupSheets.ts… スプレッドシート初期化
```

## 3. データモデル

金額は **日本円の整数**（円に補助単位が無いため小数不要）。

| テーブル | 主なフィールド | 役割 |
| --- | --- | --- |
| Users | 屋号, インボイス番号, 申告方式, 消費税区分, 端数処理 | 事業者設定 |
| Accounts | code, name, type, defaultTaxCategory | 勘定科目 |
| Partners | name, type, invoiceNumber | 取引先 |
| Transactions | date, description, kind, slipNumber | 取引（仕訳伝票） |
| JournalLines | accountId, side, amount, taxCategory, taxAmount | 仕訳明細（借方/貸方） |
| Invoices | number, issueDate, status, subtotal, taxTotal, total | 請求書 |
| InvoiceItems | description, quantity, unitPrice, taxCategory | 請求明細 |
| ShareLinks | token, scope, fiscalYear | 税理士共有リンク |

### 仕訳（複式簿記）

1 取引（Transaction）は複数の JournalLine を持ち、**借方合計＝貸方合計**で均衡する。

- 経費の簡単入力例: `借方 通信費 11,000 / 貸方 普通預金 11,000`
- 売上の簡単入力例: `借方 売掛金 330,000 / 貸方 売上高 330,000`
- 詳細仕訳モードでは任意行を追加し、リアルタイムに貸借差額を検証。

### 区分（enum 相当）

SQLite/Sheets は enum 非対応のため、`src/lib/constants.ts` に文字列コード＋ラベルを集約。

- 勘定科目区分: `ASSET / LIABILITY / EQUITY / REVENUE / EXPENSE`
- 消費税区分: `TAXABLE_10 / TAXABLE_8 / NON_TAXABLE / EXPORT_0 / OUT_OF_SCOPE`

## 4. 会計・消費税ロジック（`accounting.ts`）

- `taxFromGross(税込, 区分)`: 内税の算出（例: 11,000円/10% → 1,000円）
- `taxFromNet(税抜, 区分)`: 外税の算出
- `isBalanced(lines)`: 貸借一致の検証
- `signedAmount(type, side, amount)`: 残高集計用の符号付き金額
  （資産・費用は借方で増加、負債・純資産・収益は貸方で増加）
- `summarizeInvoiceItems(items)`: **税率区分ごとに 1 回**端数処理して請求合計を算出
  （インボイス制度の要件）

## 5. 集計・帳票（`reports.ts`）

- `profitAndLoss`: 損益計算書（収益 − 費用 ＝ 所得）
- `balanceSheet`: 貸借対照表（当期純利益を純資産に加えて均衡）
- `consumptionTaxSummary`: 売上税額 − 仕入控除（本則課税の概算）
- `monthlySeries`: 月次の売上・経費・利益（グラフ用）
- `dashboardSummary`: 主要 KPI（売上/経費/所得/現預金/売掛/買掛）

## 6. Google スプレッドシート連携

- 各テーブル＝タブ。1 行目ヘッダ、以降レコード。
- `encodeRow/decodeRow` で型（string/number/boolean）を変換。
- 追記は `values.append`、更新は id で行特定して `values.update`、削除は `deleteDimension`。
- トランザクションは無いため、明細入替などはアプリ側で順序制御。

## 7. テスト

`accounting.test.ts` / `reports.test.ts` / `data/schema.test.ts` で、
消費税計算・貸借バランス・残高集計・P/L・B/S・消費税集計・行シリアライズを検証。

```bash
npm test
```

## 8. 主な機能モジュール（追加分）

- **減価償却**（`depreciation.ts`）: 定額法（月割・備忘価額¥1）、一括償却資産（3年均等）、
  少額減価償却資産の特例（即時償却）。事業専用割合を必要経費算入額に反映。
- **青色申告決算書**（`taxReturn.ts` + `/reports/blue-return`）: 記帳データを決算書の
  各区分（収入金額・売上原価・経費・所得金額）に組み替え。青色申告特別控除を適用。
  固定資産から算出した減価償却費と帳簿の差を警告表示。印刷/PDF・CSV出力に対応。
- **領収書OCR**（`ocrParse.ts` + `ReceiptScanner`）: ブラウザ内（Tesseract.js）でOCRし
  金額・日付を抽出してフォームに自動入力。画像はcanvasで縮小して `Attachments` に保存。

## 9. 今後の拡張余地

- パスワード再設定・メール確認・OAuth ログイン
- 領収書など添付ファイルの外部ストレージ化（現状はSheetsセル上限のため縮小画像のみ）
- 棚卸・専従者給与・各種引当金、定率法、確定申告書Bや e-Tax 連携
- 簡易課税のみなし仕入率に基づく納税額の精緻化
- 本番 DB を PostgreSQL に切替（Store 実装を追加するだけ）
