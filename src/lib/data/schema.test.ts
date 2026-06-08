import { describe, expect, it } from "vitest";
import { TABLES, decodeRow, encodeRow, headerRow } from "./schema";

describe("encode/decode round-trip", () => {
  it("数値・真偽値・文字列を保持する", () => {
    const spec = TABLES.accounts;
    const obj = {
      id: "acc_1",
      userId: "user_default",
      code: "515",
      name: "通信費",
      type: "EXPENSE",
      sortOrder: 3,
      defaultTaxCategory: "TAXABLE_10",
      isSystem: true,
      isActive: false,
    };
    const row = encodeRow(spec, obj);
    const back = decodeRow(spec, row);
    expect(back.code).toBe("515");
    expect(back.sortOrder).toBe(3);
    expect(back.isSystem).toBe(true);
    expect(back.isActive).toBe(false);
  });

  it("空セルは null / false に復元", () => {
    const spec = TABLES.partners;
    const back = decodeRow(spec, ["ptn_1", "u", "名前", "VENDOR"]);
    expect(back.invoiceNumber).toBeNull();
    expect(back.email).toBeNull();
  });

  it("ヘッダはフィールド名の並び", () => {
    expect(headerRow(TABLES.users)[0]).toBe("id");
    expect(headerRow(TABLES.users)).toContain("invoiceNumber");
  });
});
