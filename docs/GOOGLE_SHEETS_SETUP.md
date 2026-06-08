# Google スプレッドシート連携の設定手順

このアプリは Google スプレッドシートをデータベースとして利用できます。
サービスアカウント（Google Cloud のロボットアカウント）を使って Sheets API 経由で
読み書きします。

## 手順

### 1. Google Cloud プロジェクトと API 有効化

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成（既存でも可）
2. 「API とサービス」→「ライブラリ」で **Google Sheets API** を有効化

### 2. サービスアカウントの作成

1. 「IAM と管理」→「サービス アカウント」→「サービス アカウントを作成」
2. 名前を付けて作成（権限は付与不要）
3. 作成したサービスアカウントの「キー」タブ →「鍵を追加」→「新しい鍵を作成」→ **JSON**
4. ダウンロードした JSON から以下を取得
   - `client_email`（例: `kaikei@my-project.iam.gserviceaccount.com`）
   - `private_key`（`-----BEGIN PRIVATE KEY-----\n...` の文字列）

### 3. `.env` の設定

```env
DATA_BACKEND=sheets
GOOGLE_SERVICE_ACCOUNT_EMAIL=kaikei@my-project.iam.gserviceaccount.com
# private_key は改行を \n のままにして、全体をダブルクォートで囲む
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n"
GOOGLE_SHEETS_SPREADSHEET_ID=
```

### 4. スプレッドシートの作成・初期化

```bash
npm run sheets:setup
```

- `GOOGLE_SHEETS_SPREADSHEET_ID` が空の場合、新規スプレッドシートを作成して
  ID と URL を表示します。表示された ID を `.env` の `GOOGLE_SHEETS_SPREADSHEET_ID` に設定してください。
- すべてのタブ（Users, Accounts, …）とヘッダ、標準勘定科目が投入されます。

### 5. スプレッドシートの共有

新規作成した場合、**所有者はサービスアカウント**です。自分（および税理士）が
ブラウザで中身を見られるように、スプレッドシートを自分の Google アカウントに
「編集者」または「閲覧者」で共有してください。

> 既存のスプレッドシートを使う場合は、先にそのスプレッドシートを
> サービスアカウントのメールアドレスに「編集者」で共有し、ID を `.env` に設定してから
> `npm run sheets:setup` を実行します。

### 6. 起動

```bash
npm run dev
```

設定画面の「データ保存先」が **Google スプレッドシート** になっていれば連携成功です。

## トラブルシューティング

| 症状 | 対処 |
| --- | --- |
| `The caller does not have permission` | スプレッドシートをサービスアカウントに共有しているか確認 |
| `Google認証情報が未設定です` | `.env` の `GOOGLE_SERVICE_ACCOUNT_EMAIL` / `GOOGLE_PRIVATE_KEY` を確認 |
| `private_key` のエラー | 改行 `\n` を保持し、全体をダブルクォートで囲む |
| デモモードのまま | `DATA_BACKEND=sheets` を設定、もしくは認証情報3点を揃える |
