// Google Sheets API クライアント（サービスアカウント認証）。
import { google, type sheets_v4 } from "googleapis";

export interface SheetsConfig {
  clientEmail: string;
  privateKey: string;
  spreadsheetId: string;
}

export function readConfig(): SheetsConfig {
  const clientEmail = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
  // .env では改行を \n でエスケープして保持することが多いので復元する
  const privateKey = process.env.GOOGLE_PRIVATE_KEY?.replace(/\\n/g, "\n");
  const spreadsheetId = process.env.GOOGLE_SHEETS_SPREADSHEET_ID;
  if (!clientEmail || !privateKey) {
    throw new Error(
      "Google認証情報が未設定です。GOOGLE_SERVICE_ACCOUNT_EMAIL と GOOGLE_PRIVATE_KEY を設定してください。",
    );
  }
  return { clientEmail, privateKey, spreadsheetId: spreadsheetId ?? "" };
}

export function getSheetsApi(cfg: SheetsConfig): sheets_v4.Sheets {
  const auth = new google.auth.JWT({
    email: cfg.clientEmail,
    key: cfg.privateKey,
    scopes: ["https://www.googleapis.com/auth/spreadsheets"],
  });
  return google.sheets({ version: "v4", auth });
}
