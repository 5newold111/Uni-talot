// 青色申告決算書（一般用）の損益計算書部の集計（純粋関数）。
// 記帳済みの仕訳から、決算書の各区分に組み替える。
import { accountBalances } from "./reports";
import type { Account, TransactionWithLines } from "./types";

export interface BlueReturnExpense {
  account: Account;
  amount: number;
}

export interface BlueReturnStatement {
  income: { sales: number; misc: number; total: number };
  cost: { opening: number; purchase: number; closing: number; total: number };
  grossProfit: number; // 差引金額（売上総利益）
  expenses: BlueReturnExpense[];
  expenseTotal: number;
  preDeductionIncome: number; // 青色申告特別控除前の所得金額
  blueDeduction: number; // 青色申告特別控除額
  incomeAmount: number; // 所得金額
  /** 固定資産から計算した当期の減価償却費（参考・未記帳分の確認用） */
  computedDepreciation: number;
}

const SALES_CODE = "401";
const MISC_CODE = "402";
const PURCHASE_CODE = "501";

export function blueReturnStatement(
  accounts: Account[],
  txs: TransactionWithLines[],
  opts: { blueDeduction: number; computedDepreciation?: number },
): BlueReturnStatement {
  const bal = accountBalances(accounts, txs);
  const balOfCode = (code: string) => {
    const a = accounts.find((x) => x.code === code);
    return a ? bal.get(a.id) ?? 0 : 0;
  };

  const revenueAccounts = accounts.filter((a) => a.type === "REVENUE");
  const totalRevenue = revenueAccounts.reduce((s, a) => s + (bal.get(a.id) ?? 0), 0);
  const sales = balOfCode(SALES_CODE);
  const misc = balOfCode(MISC_CODE) || totalRevenue - sales;
  const income = { sales, misc, total: totalRevenue };

  const purchase = balOfCode(PURCHASE_CODE);
  const cost = { opening: 0, purchase, closing: 0, total: purchase };

  const grossProfit = income.total - cost.total;

  const expenses: BlueReturnExpense[] = accounts
    .filter(
      (a) => a.type === "EXPENSE" && a.code !== PURCHASE_CODE && (bal.get(a.id) ?? 0) !== 0,
    )
    .map((a) => ({ account: a, amount: bal.get(a.id) ?? 0 }))
    .sort((a, b) => a.account.code.localeCompare(b.account.code));
  const expenseTotal = expenses.reduce((s, e) => s + e.amount, 0);

  const preDeductionIncome = grossProfit - expenseTotal;
  const blueDeduction = Math.max(
    0,
    Math.min(opts.blueDeduction, Math.max(0, preDeductionIncome)),
  );
  const incomeAmount = preDeductionIncome - blueDeduction;

  return {
    income,
    cost,
    grossProfit,
    expenses,
    expenseTotal,
    preDeductionIncome,
    blueDeduction,
    incomeAmount,
    computedDepreciation: opts.computedDepreciation ?? 0,
  };
}
