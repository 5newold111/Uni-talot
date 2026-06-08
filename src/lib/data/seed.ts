// 初期データ投入。標準勘定科目と既定ユーザー、デモ用サンプル取引を作成。
import { DEFAULT_ACCOUNTS } from "../defaultAccounts";
import type { Account, Partner, Transaction, JournalLine, User } from "../types";
import { id } from "./ids";
import type { Store } from "./store";

export const DEFAULT_USER_ID = "user_default";

export async function seedInitialData(
  store: Store,
  opts: { sample?: boolean } = {},
): Promise<void> {
  const now = new Date().toISOString();

  const user: User = {
    id: DEFAULT_USER_ID,
    email: "owner@example.com",
    name: "事業主",
    businessName: "",
    invoiceNumber: "",
    taxationType: "BLUE",
    consumptionTaxStatus: "EXEMPT",
    consumptionTaxMethod: "GENERAL",
    simplifiedBusinessType: null,
    fiscalYearStartMonth: 1,
    taxRounding: "FLOOR",
    createdAt: now,
    updatedAt: now,
  };
  await store.insert("users", user);

  const accounts: Account[] = DEFAULT_ACCOUNTS.map((a, i) => ({
    id: id("acc"),
    userId: DEFAULT_USER_ID,
    code: a.code,
    name: a.name,
    type: a.type,
    sortOrder: i,
    defaultTaxCategory: a.defaultTaxCategory ?? null,
    isSystem: true,
    isActive: true,
  }));
  await store.insertMany("accounts", accounts);

  if (!opts.sample) return;

  // ---- デモ用サンプルデータ ----
  const byCode = (code: string) => accounts.find((a) => a.code === code)!;

  const partners: Partner[] = [
    {
      id: id("ptn"),
      userId: DEFAULT_USER_ID,
      name: "株式会社サンプル商事",
      type: "CUSTOMER",
      invoiceNumber: "T1234567890123",
      email: "ap@sample.co.jp",
    },
    {
      id: id("ptn"),
      userId: DEFAULT_USER_ID,
      name: "オフィスサプライ株式会社",
      type: "VENDOR",
      invoiceNumber: "T9876543210987",
    },
  ];
  await store.insertMany("partners", partners);

  const txs: Transaction[] = [];
  const lines: JournalLine[] = [];
  let slip = 1;

  const addSimple = (
    date: string,
    description: string,
    kind: Transaction["kind"],
    debit: { account: Account; amount: number; tax: JournalLine["taxCategory"]; rate: number },
    credit: { account: Account; amount: number; tax: JournalLine["taxCategory"]; rate: number },
    partnerId?: string,
  ) => {
    const txId = id("tx");
    txs.push({
      id: txId,
      userId: DEFAULT_USER_ID,
      date,
      description,
      partnerId: partnerId ?? null,
      kind,
      slipNumber: slip++,
      note: "",
      createdAt: now,
      updatedAt: now,
    });
    const mkTax = (amount: number, cat: JournalLine["taxCategory"], rate: number) =>
      rate > 0 ? Math.floor((amount * rate) / (100 + rate)) : 0;
    lines.push({
      id: id("jl"),
      transactionId: txId,
      accountId: debit.account.id,
      side: "DEBIT",
      amount: debit.amount,
      taxCategory: debit.tax,
      taxRate: debit.rate,
      taxAmount: mkTax(debit.amount, debit.tax, debit.rate),
    });
    lines.push({
      id: id("jl"),
      transactionId: txId,
      accountId: credit.account.id,
      side: "CREDIT",
      amount: credit.amount,
      taxCategory: credit.tax,
      taxRate: credit.rate,
      taxAmount: mkTax(credit.amount, credit.tax, credit.rate),
    });
  };

  const year = new Date().getFullYear();
  const ym = (m: number, d: number) =>
    `${year}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

  // 売上（売掛）
  addSimple(
    ym(1, 31), "1月分 業務委託料", "INCOME",
    { account: byCode("111"), amount: 330000, tax: "OUT_OF_SCOPE", rate: 0 },
    { account: byCode("401"), amount: 330000, tax: "TAXABLE_10", rate: 10 },
    partners[0].id,
  );
  addSimple(
    ym(2, 28), "2月分 業務委託料", "INCOME",
    { account: byCode("111"), amount: 275000, tax: "OUT_OF_SCOPE", rate: 0 },
    { account: byCode("401"), amount: 275000, tax: "TAXABLE_10", rate: 10 },
    partners[0].id,
  );
  // 経費
  addSimple(
    ym(1, 15), "クラウド利用料", "EXPENSE",
    { account: byCode("515"), amount: 11000, tax: "TAXABLE_10", rate: 10 },
    { account: byCode("102"), amount: 11000, tax: "OUT_OF_SCOPE", rate: 0 },
  );
  addSimple(
    ym(1, 20), "事務用品 購入", "EXPENSE",
    { account: byCode("520"), amount: 5500, tax: "TAXABLE_10", rate: 10 },
    { account: byCode("101"), amount: 5500, tax: "OUT_OF_SCOPE", rate: 0 },
    partners[1].id,
  );
  addSimple(
    ym(2, 5), "電車・バス代", "EXPENSE",
    { account: byCode("514"), amount: 3200, tax: "TAXABLE_10", rate: 10 },
    { account: byCode("101"), amount: 3200, tax: "OUT_OF_SCOPE", rate: 0 },
  );
  addSimple(
    ym(2, 10), "書籍代（参考資料）", "EXPENSE",
    { account: byCode("528"), amount: 4400, tax: "TAXABLE_10", rate: 10 },
    { account: byCode("101"), amount: 4400, tax: "OUT_OF_SCOPE", rate: 0 },
  );

  await store.insertMany("transactions", txs);
  await store.insertMany("journalLines", lines);
}
