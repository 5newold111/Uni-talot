// データストアの抽象。Sheets / InMemory が実装する。
import type { TableName } from "./schema";

export interface Store {
  /** 必要なタブ・ヘッダを作成し、空なら初期データを投入する。 */
  ensureSetup(): Promise<void>;
  list<T = Record<string, unknown>>(table: TableName): Promise<T[]>;
  insert<T extends { id: string }>(table: TableName, record: T): Promise<T>;
  insertMany<T extends { id: string }>(table: TableName, records: T[]): Promise<T[]>;
  update<T extends { id: string }>(
    table: TableName,
    id: string,
    patch: Partial<T>,
  ): Promise<T>;
  remove(table: TableName, id: string): Promise<void>;
  /** バックエンド種別（UI表示用） */
  readonly kind: "sheets" | "memory";
}

let cached: Store | null = null;

/** 環境変数からバックエンドを決定して単一インスタンスを返す。 */
export async function getStore(): Promise<Store> {
  if (cached) return cached;

  const explicit = process.env.DATA_BACKEND?.toLowerCase();
  const hasSheetsCreds =
    !!process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL &&
    !!process.env.GOOGLE_PRIVATE_KEY &&
    !!process.env.GOOGLE_SHEETS_SPREADSHEET_ID;

  const useSheets =
    explicit === "sheets" || (explicit !== "memory" && hasSheetsCreds);

  if (useSheets) {
    const { SheetsStore } = await import("./sheetsStore");
    cached = new SheetsStore();
  } else {
    const { MemoryStore } = await import("./memoryStore");
    cached = new MemoryStore();
  }
  await cached.ensureSetup();
  return cached;
}

/** テスト用にキャッシュを破棄 */
export function _resetStoreCache() {
  cached = null;
}
