import { describe, expect, it } from "vitest";
import { extractAmount, extractDate, parseReceipt } from "./ocrParse";

describe("extractDate", () => {
  it("スラッシュ区切り", () => {
    expect(extractDate("2026/06/08 領収書")).toBe("2026-06-08");
  });
  it("和暦表記の年月日", () => {
    expect(extractDate("発行日 2026年6月8日")).toBe("2026-06-08");
  });
  it("不正な日付は null", () => {
    expect(extractDate("価格 1500円")).toBeNull();
  });
});

describe("extractAmount", () => {
  it("合計行の金額を優先", () => {
    const text = ["お買上げ", "小計 ¥1,000", "消費税 ¥100", "合計 ¥1,100"].join("\n");
    expect(extractAmount(text)).toBe(1100);
  });
  it("円表記・全角数字に対応", () => {
    expect(extractAmount("合計 １，２３４円")).toBe(1234);
  });
  it("キーワードが無ければ最大金額", () => {
    expect(extractAmount("A 300\nB 1,500\nC 800")).toBe(1500);
  });
});

describe("parseReceipt", () => {
  it("日付と金額をまとめて返す", () => {
    const r = parseReceipt("2026/03/15\nコンビニ\n合計 ¥748");
    expect(r.date).toBe("2026-03-15");
    expect(r.amount).toBe(748);
  });
});
