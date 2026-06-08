import { describe, expect, it } from "vitest";
import { depreciationForYear, depreciationSchedule } from "./depreciation";

const base = {
  acquisitionCost: 600000,
  usefulLife: 5,
  method: "STRAIGHT_LINE" as const,
  startDate: "2026-01-01",
  businessRatio: 100,
};

describe("定額法", () => {
  it("年初取得は耐用年数+1年で備忘価額¥1まで償却", () => {
    const sch = depreciationSchedule(base);
    // 600,000 / 5 = 120,000/年。5年で 600,000 だが ¥1 残すため最終年は調整
    expect(sch[0].depreciation).toBe(120000);
    const last = sch[sch.length - 1];
    expect(last.bookValue).toBe(1);
    const totalDep = sch.reduce((s, r) => s + r.depreciation, 0);
    expect(totalDep).toBe(599999);
  });

  it("期中取得は初年度を月割", () => {
    const sch = depreciationSchedule({ ...base, startDate: "2026-10-01" });
    // 10月供用 → 3ヶ月: 120,000 * 3/12 = 30,000
    expect(sch[0].months).toBe(3);
    expect(sch[0].depreciation).toBe(30000);
  });

  it("事業専用割合は必要経費算入額に反映（帳簿価額は満額）", () => {
    const sch = depreciationSchedule({ ...base, businessRatio: 80 });
    expect(sch[0].depreciation).toBe(120000);
    expect(sch[0].expense).toBe(96000); // 120,000 * 80%
    expect(sch[0].bookValue).toBe(480000);
  });

  it("指定年の償却額と簿価を取得できる", () => {
    expect(depreciationForYear(base, 2026).depreciation).toBe(120000);
    expect(depreciationForYear(base, 2026).bookValue).toBe(480000);
    // 償却完了後は簿価¥1のみ
    expect(depreciationForYear(base, 2099).bookValue).toBe(1);
    expect(depreciationForYear(base, 2099).depreciation).toBe(0);
  });
});

describe("一括償却資産（3年均等）", () => {
  it("取得価額を3年で均等償却し残存0", () => {
    const sch = depreciationSchedule({
      ...base,
      acquisitionCost: 180000,
      method: "LUMP_3YEAR",
    });
    expect(sch).toHaveLength(3);
    expect(sch[0].depreciation).toBe(60000);
    expect(sch[2].bookValue).toBe(0);
  });
  it("端数は最終年で調整", () => {
    const sch = depreciationSchedule({
      ...base,
      acquisitionCost: 100000,
      method: "LUMP_3YEAR",
    });
    // 33,333 + 33,333 + 33,334
    expect(sch[0].depreciation).toBe(33333);
    expect(sch[2].depreciation).toBe(33334);
    expect(sch.reduce((s, r) => s + r.depreciation, 0)).toBe(100000);
  });
});

describe("少額減価償却資産（即時償却）", () => {
  it("取得年に全額償却", () => {
    const sch = depreciationSchedule({
      ...base,
      acquisitionCost: 250000,
      method: "IMMEDIATE",
    });
    expect(sch).toHaveLength(1);
    expect(sch[0].depreciation).toBe(250000);
    expect(sch[0].bookValue).toBe(0);
  });
});
