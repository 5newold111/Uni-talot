import { describe, expect, it } from "vitest";
import { blueReturnStatement } from "./taxReturn";
import type { Account, TransactionWithLines } from "./types";

const acc = (id: string, code: string, name: string, type: Account["type"]): Account => ({
  id, userId: "u", code, name, type, sortOrder: 0,
  defaultTaxCategory: null, isSystem: true, isActive: true,
});

const accounts: Account[] = [
  acc("cash", "101", "現金", "ASSET"),
  acc("ar", "111", "売掛金", "ASSET"),
  acc("sales", "401", "売上高", "REVENUE"),
  acc("purchase", "501", "仕入高", "EXPENSE"),
  acc("comm", "515", "通信費", "EXPENSE"),
];

const line = (
  transactionId: string, accountId: string, side: "DEBIT" | "CREDIT", amount: number,
) => ({ id: id(), transactionId, accountId, side, amount, taxCategory: "OUT_OF_SCOPE" as const, taxRate: 0, taxAmount: 0 });
let _i = 0;
const id = () => `x${_i++}`;

const txs: TransactionWithLines[] = [
  {
    id: "t1", userId: "u", date: "2026-03-01", description: "売上", partnerId: null,
    kind: "INCOME", slipNumber: 1, createdAt: "", updatedAt: "",
    lines: [line("t1", "ar", "DEBIT", 1000000), line("t1", "sales", "CREDIT", 1000000)],
  },
  {
    id: "t2", userId: "u", date: "2026-03-02", description: "仕入", partnerId: null,
    kind: "EXPENSE", slipNumber: 2, createdAt: "", updatedAt: "",
    lines: [line("t2", "purchase", "DEBIT", 300000), line("t2", "cash", "CREDIT", 300000)],
  },
  {
    id: "t3", userId: "u", date: "2026-03-03", description: "通信費", partnerId: null,
    kind: "EXPENSE", slipNumber: 3, createdAt: "", updatedAt: "",
    lines: [line("t3", "comm", "DEBIT", 50000), line("t3", "cash", "CREDIT", 50000)],
  },
];

describe("blueReturnStatement", () => {
  it("売上原価・経費・控除後の所得金額を算出", () => {
    const r = blueReturnStatement(accounts, txs, { blueDeduction: 650000 });
    expect(r.income.total).toBe(1000000);
    expect(r.cost.total).toBe(300000); // 仕入高
    expect(r.grossProfit).toBe(700000);
    expect(r.expenseTotal).toBe(50000); // 通信費（仕入は原価に分離）
    expect(r.preDeductionIncome).toBe(650000); // 700,000 - 50,000
    expect(r.blueDeduction).toBe(650000);
    expect(r.incomeAmount).toBe(0);
  });

  it("控除額は控除前所得を超えない", () => {
    const small: TransactionWithLines[] = [txs[2]]; // 経費だけ→赤字
    const r = blueReturnStatement(accounts, small, { blueDeduction: 650000 });
    expect(r.preDeductionIncome).toBeLessThan(0);
    expect(r.blueDeduction).toBe(0);
    expect(r.incomeAmount).toBe(r.preDeductionIncome);
  });
});
