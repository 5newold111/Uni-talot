import { describe, expect, it } from "vitest";
import {
  applyRounding,
  creditTotal,
  debitTotal,
  increaseSide,
  isBalanced,
  signedAmount,
  summarizeInvoiceItems,
  taxFromGross,
  taxFromNet,
} from "./accounting";

describe("applyRounding", () => {
  it("各モードで丸める", () => {
    expect(applyRounding(100.6, "FLOOR")).toBe(100);
    expect(applyRounding(100.4, "CEIL")).toBe(101);
    expect(applyRounding(100.5, "ROUND")).toBe(101);
  });
});

describe("taxFromGross（税込→内税）", () => {
  it("11,000円(10%)の内税は1,000円", () => {
    expect(taxFromGross(11000, "TAXABLE_10")).toBe(1000);
  });
  it("10,800円(軽減8%)の内税は800円", () => {
    expect(taxFromGross(10800, "TAXABLE_8")).toBe(800);
  });
  it("非課税・対象外は0円", () => {
    expect(taxFromGross(11000, "NON_TAXABLE")).toBe(0);
    expect(taxFromGross(11000, "OUT_OF_SCOPE")).toBe(0);
  });
  it("端数は切り捨て（既定）", () => {
    // 1234 * 10 / 110 = 112.18..
    expect(taxFromGross(1234, "TAXABLE_10")).toBe(112);
  });
});

describe("taxFromNet（税抜→消費税）", () => {
  it("10,000円(10%)は1,000円", () => {
    expect(taxFromNet(10000, "TAXABLE_10")).toBe(1000);
  });
  it("10,000円(軽減8%)は800円", () => {
    expect(taxFromNet(10000, "TAXABLE_8")).toBe(800);
  });
});

describe("貸借バランス", () => {
  const lines = [
    { side: "DEBIT" as const, amount: 11000 },
    { side: "CREDIT" as const, amount: 11000 },
  ];
  it("借方・貸方合計", () => {
    expect(debitTotal(lines)).toBe(11000);
    expect(creditTotal(lines)).toBe(11000);
  });
  it("一致していれば balanced", () => {
    expect(isBalanced(lines)).toBe(true);
  });
  it("不一致は false", () => {
    expect(
      isBalanced([
        { side: "DEBIT", amount: 11000 },
        { side: "CREDIT", amount: 10000 },
      ]),
    ).toBe(false);
  });
  it("空配列は false", () => {
    expect(isBalanced([])).toBe(false);
  });
});

describe("勘定科目の増減方向", () => {
  it("資産・費用は借方で増加", () => {
    expect(increaseSide("ASSET")).toBe("DEBIT");
    expect(increaseSide("EXPENSE")).toBe("DEBIT");
  });
  it("負債・純資産・収益は貸方で増加", () => {
    expect(increaseSide("LIABILITY")).toBe("CREDIT");
    expect(increaseSide("EQUITY")).toBe("CREDIT");
    expect(increaseSide("REVENUE")).toBe("CREDIT");
  });
  it("signedAmount は増加方向で正、逆で負", () => {
    expect(signedAmount("REVENUE", "CREDIT", 1000)).toBe(1000);
    expect(signedAmount("REVENUE", "DEBIT", 1000)).toBe(-1000);
    expect(signedAmount("EXPENSE", "DEBIT", 1000)).toBe(1000);
  });
});

describe("summarizeInvoiceItems（税率区分ごとに端数処理）", () => {
  it("複数税率を区分ごとに集計する", () => {
    const r = summarizeInvoiceItems([
      { quantity: 2, unitPrice: 5000, taxCategory: "TAXABLE_10" }, // 10,000
      { quantity: 1, unitPrice: 3000, taxCategory: "TAXABLE_8" }, // 3,000
    ]);
    expect(r.subtotal).toBe(13000);
    // 10%: 1000, 8%: 240
    expect(r.taxTotal).toBe(1240);
    expect(r.total).toBe(14240);
    expect(r.rows).toHaveLength(2);
  });
  it("税率ごとに1回端数処理する（明細ごとに丸めない）", () => {
    // 同一区分の明細を合算してから課税: (333+333+333)=999 *10% = 99.9 -> 99
    const r = summarizeInvoiceItems([
      { quantity: 1, unitPrice: 333, taxCategory: "TAXABLE_10" },
      { quantity: 1, unitPrice: 333, taxCategory: "TAXABLE_10" },
      { quantity: 1, unitPrice: 333, taxCategory: "TAXABLE_10" },
    ]);
    expect(r.subtotal).toBe(999);
    expect(r.taxTotal).toBe(99);
  });
});
