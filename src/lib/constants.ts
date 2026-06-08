// ドメインの区分（コード値）と表示ラベルを集約。
// SQLite/Sheets では enum を使えないため、ここを唯一の正とする。

/** 勘定科目の大区分 */
export const ACCOUNT_TYPES = {
  ASSET: "資産",
  LIABILITY: "負債",
  EQUITY: "純資産",
  REVENUE: "収益",
  EXPENSE: "費用",
} as const;
export type AccountType = keyof typeof ACCOUNT_TYPES;

/** 貸借 */
export const SIDES = {
  DEBIT: "借方",
  CREDIT: "貸方",
} as const;
export type Side = keyof typeof SIDES;

/** 取引の入力種別 */
export const TX_KINDS = {
  EXPENSE: "経費",
  INCOME: "売上",
  TRANSFER: "振替",
  JOURNAL: "仕訳",
} as const;
export type TxKind = keyof typeof TX_KINDS;

/** 消費税区分 */
export const TAX_CATEGORIES = {
  TAXABLE_10: "課税10%",
  TAXABLE_8: "軽減8%",
  NON_TAXABLE: "非課税",
  EXPORT_0: "輸出免税0%",
  OUT_OF_SCOPE: "不課税・対象外",
} as const;
export type TaxCategory = keyof typeof TAX_CATEGORIES;

/** 税区分ごとの税率(%) */
export const TAX_RATE_BY_CATEGORY: Record<TaxCategory, number> = {
  TAXABLE_10: 10,
  TAXABLE_8: 8,
  NON_TAXABLE: 0,
  EXPORT_0: 0,
  OUT_OF_SCOPE: 0,
};

/** 課税方式 */
export const TAXATION_TYPES = {
  BLUE: "青色申告",
  WHITE: "白色申告",
} as const;
export type TaxationType = keyof typeof TAXATION_TYPES;

/** 消費税の納税義務 */
export const CONSUMPTION_TAX_STATUS = {
  TAXABLE: "課税事業者",
  EXEMPT: "免税事業者",
} as const;
export type ConsumptionTaxStatus = keyof typeof CONSUMPTION_TAX_STATUS;

/** 消費税計算方式 */
export const CONSUMPTION_TAX_METHOD = {
  GENERAL: "本則課税",
  SIMPLIFIED: "簡易課税",
} as const;
export type ConsumptionTaxMethod = keyof typeof CONSUMPTION_TAX_METHOD;

/** 端数処理 */
export const TAX_ROUNDING = {
  FLOOR: "切り捨て",
  ROUND: "四捨五入",
  CEIL: "切り上げ",
} as const;
export type TaxRounding = keyof typeof TAX_ROUNDING;

/** 取引先区分 */
export const PARTNER_TYPES = {
  CUSTOMER: "得意先",
  VENDOR: "仕入先",
  BOTH: "両方",
} as const;
export type PartnerType = keyof typeof PARTNER_TYPES;

/** 請求書ステータス */
export const INVOICE_STATUS = {
  DRAFT: "下書き",
  SENT: "送付済",
  PAID: "入金済",
  VOID: "無効",
} as const;
export type InvoiceStatus = keyof typeof INVOICE_STATUS;

/** 共有リンクの範囲 */
export const SHARE_SCOPES = {
  READONLY: "閲覧のみ",
  EXPORT: "エクスポート可",
} as const;
export type ShareScope = keyof typeof SHARE_SCOPES;

/** label取得ヘルパー（不正値でもクラッシュしないようにフォールバック） */
export function labelOf<T extends Record<string, string>>(
  map: T,
  key: string | null | undefined,
): string {
  if (!key) return "";
  return (map as Record<string, string>)[key] ?? key;
}
