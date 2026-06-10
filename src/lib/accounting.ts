// 会計・消費税計算の中核ロジック（副作用なし・テスト対象）。
import {
  TAX_RATE_BY_CATEGORY,
  type AccountType,
  type Side,
  type TaxCategory,
  type TaxRounding,
} from "./constants";
import type { InvoiceItem, JournalLine } from "./types";

/** 端数処理 */
export function applyRounding(value: number, mode: TaxRounding): number {
  switch (mode) {
    case "ROUND":
      return Math.round(value);
    case "CEIL":
      return Math.ceil(value);
    case "FLOOR":
    default:
      return Math.floor(value);
  }
}

/**
 * 税込金額から内消費税額を算出する。
 * 例: 11,000円(課税10%) → 1,000円
 */
export function taxFromGross(
  gross: number,
  taxCategory: TaxCategory,
  rounding: TaxRounding = "FLOOR",
): number {
  const rate = TAX_RATE_BY_CATEGORY[taxCategory];
  if (!rate) return 0;
  return applyRounding((gross * rate) / (100 + rate), rounding);
}

/**
 * 税抜金額から消費税額を算出する（請求書の明細など）。
 * 例: 10,000円(課税10%) → 1,000円
 */
export function taxFromNet(
  net: number,
  taxCategory: TaxCategory,
  rounding: TaxRounding = "FLOOR",
): number {
  const rate = TAX_RATE_BY_CATEGORY[taxCategory];
  if (!rate) return 0;
  return applyRounding((net * rate) / 100, rounding);
}

/** 仕訳の貸借が一致しているか */
export function debitTotal(lines: Pick<JournalLine, "side" | "amount">[]): number {
  return lines
    .filter((l) => l.side === "DEBIT")
    .reduce((s, l) => s + (l.amount || 0), 0);
}

export function creditTotal(lines: Pick<JournalLine, "side" | "amount">[]): number {
  return lines
    .filter((l) => l.side === "CREDIT")
    .reduce((s, l) => s + (l.amount || 0), 0);
}

export function isBalanced(
  lines: Pick<JournalLine, "side" | "amount">[],
): boolean {
  return debitTotal(lines) === creditTotal(lines) && lines.length > 0;
}

/**
 * 勘定科目区分における「増加」がどちらの貸借に立つか。
 * 資産・費用は借方で増加、負債・純資産・収益は貸方で増加。
 */
export function increaseSide(type: AccountType): Side {
  return type === "ASSET" || type === "EXPENSE" ? "DEBIT" : "CREDIT";
}

/**
 * ある科目区分に対し、指定された貸借が「プラス（増加）」なら +amount、
 * 逆方向なら -amount を返す。残高集計に用いる。
 */
export function signedAmount(
  type: AccountType,
  side: Side,
  amount: number,
): number {
  return side === increaseSide(type) ? amount : -amount;
}

export interface TaxBreakdownRow {
  taxCategory: TaxCategory;
  rate: number;
  /** 税抜（本体）合計 */
  net: number;
  /** 消費税合計 */
  tax: number;
  /** 税込合計 */
  gross: number;
}

/**
 * 請求明細から税率区分ごとの内訳と合計を算出する。
 * インボイス制度では「税率ごとに1回」端数処理する必要があるため、
 * 区分ごとに税抜を合算してから消費税を計算する。
 */
export function summarizeInvoiceItems(
  items: Pick<InvoiceItem, "quantity" | "unitPrice" | "taxCategory">[],
  rounding: TaxRounding = "FLOOR",
): { rows: TaxBreakdownRow[]; subtotal: number; taxTotal: number; total: number } {
  const byCategory = new Map<TaxCategory, number>();
  for (const item of items) {
    const net = (item.quantity || 0) * (item.unitPrice || 0);
    byCategory.set(
      item.taxCategory,
      (byCategory.get(item.taxCategory) || 0) + net,
    );
  }

  const rows: TaxBreakdownRow[] = [];
  for (const [taxCategory, net] of byCategory) {
    const tax = taxFromNet(net, taxCategory, rounding);
    rows.push({
      taxCategory,
      rate: TAX_RATE_BY_CATEGORY[taxCategory],
      net,
      tax,
      gross: net + tax,
    });
  }
  rows.sort((a, b) => b.rate - a.rate);

  const subtotal = rows.reduce((s, r) => s + r.net, 0);
  const taxTotal = rows.reduce((s, r) => s + r.tax, 0);
  return { rows, subtotal, taxTotal, total: subtotal + taxTotal };
}
