import { describe, expect, it } from "vitest";
import {
  createSessionToken,
  hashPassword,
  verifyPassword,
  verifySessionToken,
} from "./auth";

describe("password hashing", () => {
  it("正しいパスワードを検証できる", () => {
    const stored = hashPassword("s3cret-pass");
    expect(verifyPassword("s3cret-pass", stored)).toBe(true);
  });
  it("誤ったパスワードは拒否", () => {
    const stored = hashPassword("s3cret-pass");
    expect(verifyPassword("wrong", stored)).toBe(false);
  });
  it("ハッシュは毎回異なる（ソルト）", () => {
    expect(hashPassword("x")).not.toBe(hashPassword("x"));
  });
  it("未設定の保存値は false", () => {
    expect(verifyPassword("x", undefined)).toBe(false);
    expect(verifyPassword("x", "")).toBe(false);
  });
});

describe("session token", () => {
  it("発行したトークンからユーザーIDを復元できる", () => {
    const t = createSessionToken("user_abc");
    expect(verifySessionToken(t)).toBe("user_abc");
  });
  it("改ざんされたトークンは拒否", () => {
    const t = createSessionToken("user_abc");
    const tampered = t.slice(0, -2) + "xy";
    expect(verifySessionToken(tampered)).toBeNull();
  });
  it("不正な形式は null", () => {
    expect(verifySessionToken("garbage")).toBeNull();
    expect(verifySessionToken(undefined)).toBeNull();
  });
});
