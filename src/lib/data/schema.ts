// スプレッドシートの「タブ＝テーブル」「列＝フィールド」の定義。
// Sheets / InMemory どちらのストアもこの定義を共有する。

export type FieldType = "string" | "number" | "boolean" | "json";

export interface FieldSpec {
  key: string;
  type: FieldType;
}

export interface TableSpec {
  /** スプレッドシートのタブ名 */
  sheet: string;
  fields: readonly FieldSpec[];
}

const s = (key: string): FieldSpec => ({ key, type: "string" });
const n = (key: string): FieldSpec => ({ key, type: "number" });
const b = (key: string): FieldSpec => ({ key, type: "boolean" });

export const TABLES = {
  users: {
    sheet: "Users",
    fields: [
      s("id"),
      s("email"),
      s("name"),
      s("passwordHash"),
      s("businessName"),
      s("invoiceNumber"),
      s("taxationType"),
      s("consumptionTaxStatus"),
      s("consumptionTaxMethod"),
      n("simplifiedBusinessType"),
      n("fiscalYearStartMonth"),
      s("taxRounding"),
      n("blueDeduction"),
      s("createdAt"),
      s("updatedAt"),
    ],
  },
  accounts: {
    sheet: "Accounts",
    fields: [
      s("id"),
      s("userId"),
      s("code"),
      s("name"),
      s("type"),
      n("sortOrder"),
      s("defaultTaxCategory"),
      b("isSystem"),
      b("isActive"),
    ],
  },
  partners: {
    sheet: "Partners",
    fields: [
      s("id"),
      s("userId"),
      s("name"),
      s("type"),
      s("invoiceNumber"),
      s("email"),
      s("phone"),
      s("address"),
      s("note"),
    ],
  },
  transactions: {
    sheet: "Transactions",
    fields: [
      s("id"),
      s("userId"),
      s("date"),
      s("description"),
      s("partnerId"),
      s("kind"),
      n("slipNumber"),
      s("note"),
      s("createdAt"),
      s("updatedAt"),
    ],
  },
  journalLines: {
    sheet: "JournalLines",
    fields: [
      s("id"),
      s("transactionId"),
      s("accountId"),
      s("side"),
      n("amount"),
      s("taxCategory"),
      n("taxRate"),
      n("taxAmount"),
      s("description"),
    ],
  },
  invoices: {
    sheet: "Invoices",
    fields: [
      s("id"),
      s("userId"),
      s("partnerId"),
      s("number"),
      s("issueDate"),
      s("dueDate"),
      s("status"),
      n("subtotal"),
      n("taxTotal"),
      n("total"),
      s("note"),
      s("createdAt"),
      s("updatedAt"),
    ],
  },
  invoiceItems: {
    sheet: "InvoiceItems",
    fields: [
      s("id"),
      s("invoiceId"),
      s("description"),
      n("quantity"),
      n("unitPrice"),
      s("taxCategory"),
      n("taxRate"),
      n("sortOrder"),
    ],
  },
  attachments: {
    sheet: "Attachments",
    fields: [
      s("id"),
      s("userId"),
      s("transactionId"),
      s("fileName"),
      s("mimeType"),
      s("dataUrl"),
      s("ocrText"),
      s("createdAt"),
    ],
  },
  fixedAssets: {
    sheet: "FixedAssets",
    fields: [
      s("id"),
      s("userId"),
      s("name"),
      s("acquisitionDate"),
      s("startDate"),
      n("acquisitionCost"),
      n("usefulLife"),
      s("method"),
      n("businessRatio"),
      s("accountId"),
      s("note"),
      s("createdAt"),
    ],
  },
  shareLinks: {
    sheet: "ShareLinks",
    fields: [
      s("id"),
      s("userId"),
      s("token"),
      s("label"),
      s("scope"),
      n("fiscalYear"),
      s("expiresAt"),
      s("revokedAt"),
      s("createdAt"),
    ],
  },
} as const;

export type TableName = keyof typeof TABLES;

export const TABLE_NAMES = Object.keys(TABLES) as TableName[];

/** オブジェクト → 行(string[])。Sheets セルは文字列で持つ。 */
export function encodeRow(spec: TableSpec, obj: Record<string, unknown>): string[] {
  return spec.fields.map((f) => {
    const v = obj[f.key];
    if (v === undefined || v === null) return "";
    if (f.type === "boolean") return v ? "TRUE" : "FALSE";
    if (f.type === "json") return JSON.stringify(v);
    return String(v);
  });
}

/** 行(string[]) → オブジェクト */
export function decodeRow(spec: TableSpec, row: string[]): Record<string, unknown> {
  const obj: Record<string, unknown> = {};
  spec.fields.forEach((f, i) => {
    const raw = row[i] ?? "";
    if (raw === "") {
      obj[f.key] = f.type === "boolean" ? false : null;
      return;
    }
    switch (f.type) {
      case "number":
        obj[f.key] = Number(raw);
        break;
      case "boolean":
        obj[f.key] = raw === "TRUE" || raw === "true" || raw === "1";
        break;
      case "json":
        try {
          obj[f.key] = JSON.parse(raw);
        } catch {
          obj[f.key] = null;
        }
        break;
      default:
        obj[f.key] = raw;
    }
  });
  return obj;
}

export function headerRow(spec: TableSpec): string[] {
  return spec.fields.map((f) => f.key);
}
