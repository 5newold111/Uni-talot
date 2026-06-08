// インメモリ・ストア。認証情報が無くてもアプリを起動・テストできるようにする。
// プロセス内で永続するためデモに十分。再起動で消える。
import { seedInitialData } from "./seed";
import type { TableName } from "./schema";
import type { Store } from "./store";

type Row = Record<string, unknown> & { id: string };

// dev のホットリロードでも保持されるよう globalThis に退避
const g = globalThis as unknown as { __memTables?: Map<TableName, Row[]> };

export class MemoryStore implements Store {
  readonly kind = "memory" as const;
  private tables: Map<TableName, Row[]>;

  constructor() {
    if (!g.__memTables) g.__memTables = new Map();
    this.tables = g.__memTables;
  }

  private tableOf(name: TableName): Row[] {
    let t = this.tables.get(name);
    if (!t) {
      t = [];
      this.tables.set(name, t);
    }
    return t;
  }

  async ensureSetup(): Promise<void> {
    const users = this.tableOf("users");
    if (users.length === 0) {
      // デモモードはサンプル取引込みで投入し、すぐ画面を確認できるようにする
      await seedInitialData(this, { sample: true });
    }
  }

  async list<T = Record<string, unknown>>(table: TableName): Promise<T[]> {
    return this.tableOf(table).map((r) => ({ ...r })) as T[];
  }

  async insert<T extends { id: string }>(table: TableName, record: T): Promise<T> {
    this.tableOf(table).push({ ...(record as Row) });
    return record;
  }

  async insertMany<T extends { id: string }>(
    table: TableName,
    records: T[],
  ): Promise<T[]> {
    const t = this.tableOf(table);
    for (const r of records) t.push({ ...(r as Row) });
    return records;
  }

  async update<T extends { id: string }>(
    table: TableName,
    id: string,
    patch: Partial<T>,
  ): Promise<T> {
    const t = this.tableOf(table);
    const idx = t.findIndex((r) => r.id === id);
    if (idx === -1) throw new Error(`${table}: id=${id} not found`);
    t[idx] = { ...t[idx], ...(patch as Row) };
    return t[idx] as T;
  }

  async remove(table: TableName, id: string): Promise<void> {
    const t = this.tableOf(table);
    const idx = t.findIndex((r) => r.id === id);
    if (idx !== -1) t.splice(idx, 1);
  }
}
