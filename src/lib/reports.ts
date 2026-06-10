// 集計・帳票ロジック（純粋関数）。Account[] と TransactionWithLines[] を受け取り計算する。
import { signedAmount } from "./accounting";
import type { TaxCategory } from "./constants";
import { TAX_CATEGORIES } from "./constants";
import type { Account, TransactionWithLines } from "./types";

export interface AccountAmount {
  account: Account;
  amount: number;
}

function accountMap(accounts: Account[]): Map<string, Account> {
  return new Map(accounts.map((a) => [a.id, a]));
}

/** 科目ごとの符号付き残高（増加方向を正）。 */
export function accountBalances(
  accounts: Account[],
  txs: TransactionWithLines[],
): Map<string, number> {
  const map = accountMap(accounts);
  const bal = new Map<string, number>();
  for (const tx of txs) {
    for (const l of tx.lines) {
      const acc = map.get(l.accountId);
      if (!acc) continue;
      const v = signedAmount(acc.type, l.side, l.amount);
      bal.set(l.accountId, (bal.get(l.accountId) ?? 0) + v);
    }
  }
  return bal;
}

export interface ProfitAndLoss {
  revenue: AccountAmount[];
  expense: AccountAmount[];
  totalRevenue: number;
  totalExpense: number;
  netIncome: number;
}

/** 損益計算書 */
export function profitAndLoss(
  accounts: Account[],
  txs: TransactionWithLines[],
): ProfitAndLoss {
  const bal = accountBalances(accounts, txs);
  const pick = (type: Account["type"]): AccountAmount[] =>
    accounts
      .filter((a) => a.type === type && (bal.get(a.id) ?? 0) !== 0)
      .map((a) => ({ account: a, amount: bal.get(a.id) ?? 0 }))
      .sort((a, b) => a.account.code.localeCompare(b.account.code));

  const revenue = pick("REVENUE");
  const expense = pick("EXPENSE");
  const totalRevenue = revenue.reduce((s, r) => s + r.amount, 0);
  const totalExpense = expense.reduce((s, r) => s + r.amount, 0);
  return {
    revenue,
    expense,
    totalRevenue,
    totalExpense,
    netIncome: totalRevenue - totalExpense,
  };
}

export interface BalanceSheet {
  assets: AccountAmount[];
  liabilities: AccountAmount[];
  equity: AccountAmount[];
  totalAssets: number;
  totalLiabilities: number;
  totalEquity: number;
  netIncome: number;
}

/** 貸借対照表（当期純利益を純資産に加えてバランスさせる） */
export function balanceSheet(
  accounts: Account[],
  txs: TransactionWithLines[],
): BalanceSheet {
  const bal = accountBalances(accounts, txs);
  const pl = profitAndLoss(accounts, txs);
  const pick = (type: Account["type"]): AccountAmount[] =>
    accounts
      .filter((a) => a.type === type && (bal.get(a.id) ?? 0) !== 0)
      .map((a) => ({ account: a, amount: bal.get(a.id) ?? 0 }))
      .sort((a, b) => a.account.code.localeCompare(b.account.code));

  const assets = pick("ASSET");
  const liabilities = pick("LIABILITY");
  const equity = pick("EQUITY");
  const totalAssets = assets.reduce((s, r) => s + r.amount, 0);
  const totalLiabilities = liabilities.reduce((s, r) => s + r.amount, 0);
  const totalEquity =
    equity.reduce((s, r) => s + r.amount, 0) + pl.netIncome;
  return {
    assets,
    liabilities,
    equity,
    totalAssets,
    totalLiabilities,
    totalEquity,
    netIncome: pl.netIncome,
  };
}

export interface TaxSummaryRow {
  taxCategory: TaxCategory;
  label: string;
  rate: number;
  base: number; // 税抜換算ベース（本体）
  tax: number; // 消費税額
}

export interface ConsumptionTaxSummary {
  sales: TaxSummaryRow[];
  purchase: TaxSummaryRow[];
  salesTaxTotal: number;
  purchaseTaxTotal: number;
  /** 本則課税での納付見込（売上にかかる消費税 − 仕入控除） */
  estimatedPayable: number;
}

/** 消費税集計（本則課税ベースの概算） */
export function consumptionTaxSummary(
  accounts: Account[],
  txs: TransactionWithLines[],
): ConsumptionTaxSummary {
  const map = accountMap(accounts);
  const salesAgg = new Map<TaxCategory, { base: number; tax: number }>();
  const purchaseAgg = new Map<TaxCategory, { base: number; tax: number }>();

  for (const tx of txs) {
    for (const l of tx.lines) {
      const acc = map.get(l.accountId);
      if (!acc) continue;
      const isSales = acc.type === "REVENUE";
      const isPurchase = acc.type === "EXPENSE" || acc.type === "ASSET";
      if (!isSales && !isPurchase) continue;
      if (l.taxRate === 0 && l.taxAmount === 0) continue;
      const target = isSales ? salesAgg : purchaseAgg;
      const cur = target.get(l.taxCategory) ?? { base: 0, tax: 0 };
      cur.base += l.amount - l.taxAmount;
      cur.tax += l.taxAmount;
      target.set(l.taxCategory, cur);
    }
  }

  const toRows = (agg: Map<TaxCategory, { base: number; tax: number }>): TaxSummaryRow[] =>
    [...agg.entries()]
      .map(([taxCategory, v]) => ({
        taxCategory,
        label: TAX_CATEGORIES[taxCategory],
        rate:
          taxCategory === "TAXABLE_10" ? 10 : taxCategory === "TAXABLE_8" ? 8 : 0,
        base: v.base,
        tax: v.tax,
      }))
      .sort((a, b) => b.rate - a.rate);

  const sales = toRows(salesAgg);
  const purchase = toRows(purchaseAgg);
  const salesTaxTotal = sales.reduce((s, r) => s + r.tax, 0);
  const purchaseTaxTotal = purchase.reduce((s, r) => s + r.tax, 0);
  return {
    sales,
    purchase,
    salesTaxTotal,
    purchaseTaxTotal,
    estimatedPayable: salesTaxTotal - purchaseTaxTotal,
  };
}

export interface MonthlyPoint {
  month: string; // "1" .. "12"
  label: string; // "1月"
  revenue: number;
  expense: number;
  profit: number;
}

/** 月次の売上・経費・利益（指定年）。グラフ用。 */
export function monthlySeries(
  accounts: Account[],
  txs: TransactionWithLines[],
  year: number,
): MonthlyPoint[] {
  const map = accountMap(accounts);
  const points: MonthlyPoint[] = Array.from({ length: 12 }, (_, i) => ({
    month: String(i + 1),
    label: `${i + 1}月`,
    revenue: 0,
    expense: 0,
    profit: 0,
  }));
  for (const tx of txs) {
    const d = new Date(tx.date);
    if (d.getFullYear() !== year) continue;
    const m = d.getMonth();
    for (const l of tx.lines) {
      const acc = map.get(l.accountId);
      if (!acc) continue;
      if (acc.type === "REVENUE")
        points[m].revenue += signedAmount(acc.type, l.side, l.amount);
      if (acc.type === "EXPENSE")
        points[m].expense += signedAmount(acc.type, l.side, l.amount);
    }
  }
  for (const p of points) p.profit = p.revenue - p.expense;
  return points;
}

/** ダッシュボード用サマリ */
export interface DashboardSummary {
  totalRevenue: number;
  totalExpense: number;
  netIncome: number;
  txCount: number;
  receivable: number; // 売掛金残高
  payable: number; // 買掛金+未払金残高
  cash: number; // 現金+預金残高
}

export function dashboardSummary(
  accounts: Account[],
  txs: TransactionWithLines[],
): DashboardSummary {
  const pl = profitAndLoss(accounts, txs);
  const bal = accountBalances(accounts, txs);
  const sumByCodes = (codes: string[]) =>
    accounts
      .filter((a) => codes.includes(a.code))
      .reduce((s, a) => s + (bal.get(a.id) ?? 0), 0);
  return {
    totalRevenue: pl.totalRevenue,
    totalExpense: pl.totalExpense,
    netIncome: pl.netIncome,
    txCount: txs.length,
    receivable: sumByCodes(["111"]),
    payable: sumByCodes(["201", "202"]),
    cash: sumByCodes(["101", "102"]),
  };
}
