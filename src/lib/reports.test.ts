import { describe, expect, it } from "vitest";
import {
  accountBalances,
  balanceSheet,
  consumptionTaxSummary,
  dashboardSummary,
  monthlySeries,
  profitAndLoss,
} from "./reports";
import type { Account, TransactionWithLines } from "./types";

const acc = (
  id: string,
  code: string,
  name: string,
  type: Account["type"],
): Account => ({
  id,
  userId: "u",
  code,
  name,
  type,
  sortOrder: 0,
  defaultTaxCategory: null,
  isSystem: true,
  isActive: true,
});

const accounts: Account[] = [
  acc("cash", "101", "現金", "ASSET"),
  acc("ar", "111", "売掛金", "ASSET"),
  acc("ap", "202", "未払金", "LIABILITY"),
  acc("sales", "401", "売上高", "REVENUE"),
  acc("comm", "515", "通信費", "EXPENSE"),
];

// 売上 330,000(税込/売掛) と 通信費 11,000(税込/現金)
const txs: TransactionWithLines[] = [
  {
    id: "t1",
    userId: "u",
    date: "2026-01-31",
    description: "売上",
    partnerId: null,
    kind: "INCOME",
    slipNumber: 1,
    createdAt: "",
    updatedAt: "",
    lines: [
      {
        id: "l1",
        transactionId: "t1",
        accountId: "ar",
        side: "DEBIT",
        amount: 330000,
        taxCategory: "OUT_OF_SCOPE",
        taxRate: 0,
        taxAmount: 0,
      },
      {
        id: "l2",
        transactionId: "t1",
        accountId: "sales",
        side: "CREDIT",
        amount: 330000,
        taxCategory: "TAXABLE_10",
        taxRate: 10,
        taxAmount: 30000,
      },
    ],
  },
  {
    id: "t2",
    userId: "u",
    date: "2026-02-15",
    description: "通信費",
    partnerId: null,
    kind: "EXPENSE",
    slipNumber: 2,
    createdAt: "",
    updatedAt: "",
    lines: [
      {
        id: "l3",
        transactionId: "t2",
        accountId: "comm",
        side: "DEBIT",
        amount: 11000,
        taxCategory: "TAXABLE_10",
        taxRate: 10,
        taxAmount: 1000,
      },
      {
        id: "l4",
        transactionId: "t2",
        accountId: "cash",
        side: "CREDIT",
        amount: 11000,
        taxCategory: "OUT_OF_SCOPE",
        taxRate: 0,
        taxAmount: 0,
      },
    ],
  },
];

describe("accountBalances", () => {
  it("符号付き残高を集計する", () => {
    const b = accountBalances(accounts, txs);
    expect(b.get("ar")).toBe(330000); // 資産・借方で増加
    expect(b.get("sales")).toBe(330000); // 収益・貸方で増加
    expect(b.get("comm")).toBe(11000); // 費用・借方で増加
    expect(b.get("cash")).toBe(-11000); // 現金は貸方なので減少
  });
});

describe("profitAndLoss", () => {
  it("売上・経費・純利益", () => {
    const pl = profitAndLoss(accounts, txs);
    expect(pl.totalRevenue).toBe(330000);
    expect(pl.totalExpense).toBe(11000);
    expect(pl.netIncome).toBe(319000);
  });
});

describe("balanceSheet", () => {
  it("資産=負債+純資産（純利益込み）でバランスする", () => {
    const bs = balanceSheet(accounts, txs);
    // 資産: 売掛 330,000 - 現金 11,000 = 319,000
    expect(bs.totalAssets).toBe(319000);
    // 純資産 = 当期純利益 319,000、負債 0
    expect(bs.totalLiabilities + bs.totalEquity).toBe(bs.totalAssets);
  });
});

describe("consumptionTaxSummary", () => {
  it("売上の消費税と仕入控除、納付見込", () => {
    const t = consumptionTaxSummary(accounts, txs);
    expect(t.salesTaxTotal).toBe(30000);
    expect(t.purchaseTaxTotal).toBe(1000);
    expect(t.estimatedPayable).toBe(29000);
  });
});

describe("monthlySeries", () => {
  it("月ごとに売上・経費を割り当てる", () => {
    const m = monthlySeries(accounts, txs, 2026);
    expect(m[0].revenue).toBe(330000); // 1月
    expect(m[1].expense).toBe(11000); // 2月
    expect(m[0].profit).toBe(330000);
  });
});

describe("dashboardSummary", () => {
  it("主要指標", () => {
    const s = dashboardSummary(accounts, txs);
    expect(s.netIncome).toBe(319000);
    expect(s.receivable).toBe(330000);
    expect(s.cash).toBe(-11000);
    expect(s.txCount).toBe(2);
  });
});
