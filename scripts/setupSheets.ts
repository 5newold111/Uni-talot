// Google スプレッドシートを初期化するセットアップスクリプト。
//   npm run sheets:setup
//
// 動作:
//   - GOOGLE_SHEETS_SPREADSHEET_ID が未設定なら新規スプレッドシートを作成し、IDを表示
//   - 既存IDがあれば、不足タブ・ヘッダを作成し、空なら標準勘定科目を投入
//
// 事前準備（.env）:
//   GOOGLE_SERVICE_ACCOUNT_EMAIL, GOOGLE_PRIVATE_KEY を設定し、
//   Sheets API を有効化したサービスアカウントを用意してください。
import { getSheetsApi, readConfig } from "../src/lib/data/sheetsClient";

async function main() {
  // Node 20.12+ / 22 の .env ローダ
  try {
    (process as NodeJS.Process & { loadEnvFile?: (p?: string) => void }).loadEnvFile?.(".env");
  } catch {
    // .env が無くても環境変数があれば続行
  }

  const cfg = readConfig();
  const api = getSheetsApi(cfg);

  let spreadsheetId = cfg.spreadsheetId;

  if (!spreadsheetId) {
    console.log("新規スプレッドシートを作成します…");
    const created = await api.spreadsheets.create({
      requestBody: {
        properties: { title: "会計フリー帳 データ" },
      },
    });
    spreadsheetId = created.data.spreadsheetId!;
    console.log("\n✅ 作成しました。");
    console.log(`   スプレッドシートID: ${spreadsheetId}`);
    console.log(`   URL: https://docs.google.com/spreadsheets/d/${spreadsheetId}/edit`);
    console.log("\n次の操作を行ってください:");
    console.log(`   1) .env に GOOGLE_SHEETS_SPREADSHEET_ID=${spreadsheetId} を追記`);
    console.log(`   2) このスプレッドシートを自分のGoogleアカウントに「編集者」で共有`);
    console.log(`      （所有者はサービスアカウント ${cfg.clientEmail} です）`);
    // 続けてタブ作成・初期データ投入
    process.env.GOOGLE_SHEETS_SPREADSHEET_ID = spreadsheetId;
  }

  process.env.GOOGLE_SHEETS_SPREADSHEET_ID = spreadsheetId;
  process.env.DATA_BACKEND = "sheets";

  const { SheetsStore } = await import("../src/lib/data/sheetsStore");
  const store = new SheetsStore();
  console.log("\nタブとヘッダ、初期勘定科目をセットアップ中…");
  await store.ensureSetup();
  console.log("✅ セットアップ完了。アプリから利用できます。");
}

main().catch((e) => {
  console.error("❌ セットアップに失敗しました:", e?.message ?? e);
  process.exit(1);
});
