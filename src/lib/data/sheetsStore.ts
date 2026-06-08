// Google スプレッドシートをデータストアとして使う実装。
// 各タブを1テーブルとし、1行目をヘッダとして読み書きする。
//
// 注意: Sheets API はトランザクションを持たない。単一ユーザーの記帳用途では
// 十分だが、整合性が重要な操作はアプリ側で順序を制御する。
import {
  TABLES,
  decodeRow,
  encodeRow,
  headerRow,
  type TableName,
} from "./schema";
import { getSheetsApi, readConfig, type SheetsConfig } from "./sheetsClient";
import { seedInitialData } from "./seed";
import type { Store } from "./store";
import type { sheets_v4 } from "googleapis";

export class SheetsStore implements Store {
  readonly kind = "sheets" as const;
  private cfg: SheetsConfig;
  private api: sheets_v4.Sheets;

  constructor() {
    this.cfg = readConfig();
    if (!this.cfg.spreadsheetId) {
      throw new Error(
        "GOOGLE_SHEETS_SPREADSHEET_ID が未設定です。`npm run sheets:setup` で作成してください。",
      );
    }
    this.api = getSheetsApi(this.cfg);
  }

  private get spreadsheetId() {
    return this.cfg.spreadsheetId;
  }

  /** タブが無ければ作成し、ヘッダを書き込む。空なら初期データ投入。 */
  async ensureSetup(): Promise<void> {
    const meta = await this.api.spreadsheets.get({
      spreadsheetId: this.spreadsheetId,
    });
    const existing = new Set(
      (meta.data.sheets ?? []).map((sh) => sh.properties?.title),
    );

    const toCreate = (Object.keys(TABLES) as TableName[]).filter(
      (t) => !existing.has(TABLES[t].sheet),
    );
    if (toCreate.length > 0) {
      await this.api.spreadsheets.batchUpdate({
        spreadsheetId: this.spreadsheetId,
        requestBody: {
          requests: toCreate.map((t) => ({
            addSheet: { properties: { title: TABLES[t].sheet } },
          })),
        },
      });
      // 各新規タブにヘッダを書く
      for (const t of toCreate) {
        await this.writeHeader(t);
      }
    }

    // users が空なら初期データ投入
    const users = await this.list("users");
    if (users.length === 0) {
      await seedInitialData(this, { sample: false });
    }
  }

  private async writeHeader(table: TableName): Promise<void> {
    const spec = TABLES[table];
    await this.api.spreadsheets.values.update({
      spreadsheetId: this.spreadsheetId,
      range: `${spec.sheet}!A1`,
      valueInputOption: "RAW",
      requestBody: { values: [headerRow(spec)] },
    });
  }

  async list<T = Record<string, unknown>>(table: TableName): Promise<T[]> {
    const spec = TABLES[table];
    const res = await this.api.spreadsheets.values.get({
      spreadsheetId: this.spreadsheetId,
      range: `${spec.sheet}!A2:ZZ`,
    });
    const rows = res.data.values ?? [];
    return rows
      .filter((r) => r.length > 0 && r[0])
      .map((r) => decodeRow(spec, r as string[])) as T[];
  }

  async insert<T extends { id: string }>(table: TableName, record: T): Promise<T> {
    const spec = TABLES[table];
    await this.api.spreadsheets.values.append({
      spreadsheetId: this.spreadsheetId,
      range: `${spec.sheet}!A1`,
      valueInputOption: "RAW",
      insertDataOption: "INSERT_ROWS",
      requestBody: { values: [encodeRow(spec, record)] },
    });
    return record;
  }

  async insertMany<T extends { id: string }>(
    table: TableName,
    records: T[],
  ): Promise<T[]> {
    if (records.length === 0) return records;
    const spec = TABLES[table];
    await this.api.spreadsheets.values.append({
      spreadsheetId: this.spreadsheetId,
      range: `${spec.sheet}!A1`,
      valueInputOption: "RAW",
      insertDataOption: "INSERT_ROWS",
      requestBody: { values: records.map((r) => encodeRow(spec, r)) },
    });
    return records;
  }

  /** id の行番号(1始まり、ヘッダ込み)を探す */
  private async findRowNumber(table: TableName, id: string): Promise<number | null> {
    const spec = TABLES[table];
    const res = await this.api.spreadsheets.values.get({
      spreadsheetId: this.spreadsheetId,
      range: `${spec.sheet}!A2:A`,
    });
    const ids = res.data.values ?? [];
    const idx = ids.findIndex((r) => r[0] === id);
    return idx === -1 ? null : idx + 2; // +2: ヘッダ行 + 0始まり補正
  }

  async update<T extends { id: string }>(
    table: TableName,
    id: string,
    patch: Partial<T>,
  ): Promise<T> {
    const spec = TABLES[table];
    const rowNum = await this.findRowNumber(table, id);
    if (rowNum === null) throw new Error(`${table}: id=${id} not found`);

    // 既存行を読み、patch をマージして書き戻す
    const res = await this.api.spreadsheets.values.get({
      spreadsheetId: this.spreadsheetId,
      range: `${spec.sheet}!A${rowNum}:ZZ${rowNum}`,
    });
    const current = decodeRow(spec, (res.data.values?.[0] ?? []) as string[]);
    const merged = { ...current, ...patch, id } as Record<string, unknown>;
    await this.api.spreadsheets.values.update({
      spreadsheetId: this.spreadsheetId,
      range: `${spec.sheet}!A${rowNum}`,
      valueInputOption: "RAW",
      requestBody: { values: [encodeRow(spec, merged)] },
    });
    return merged as T;
  }

  async remove(table: TableName, id: string): Promise<void> {
    const spec = TABLES[table];
    const rowNum = await this.findRowNumber(table, id);
    if (rowNum === null) return;

    // 該当タブの sheetId を取得して行削除
    const meta = await this.api.spreadsheets.get({
      spreadsheetId: this.spreadsheetId,
    });
    const sheet = (meta.data.sheets ?? []).find(
      (sh) => sh.properties?.title === spec.sheet,
    );
    const sheetId = sheet?.properties?.sheetId;
    if (sheetId == null) return;

    await this.api.spreadsheets.batchUpdate({
      spreadsheetId: this.spreadsheetId,
      requestBody: {
        requests: [
          {
            deleteDimension: {
              range: {
                sheetId,
                dimension: "ROWS",
                startIndex: rowNum - 1,
                endIndex: rowNum,
              },
            },
          },
        ],
      },
    });
  }
}
