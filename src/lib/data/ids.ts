import { randomUUID } from "node:crypto";

/** 接頭辞付きの一意ID。例: id("tx") => "tx_3f9a..." */
export function id(prefix: string): string {
  return `${prefix}_${randomUUID().replace(/-/g, "").slice(0, 20)}`;
}

/** 共有リンク等のランダムトークン */
export function token(): string {
  return randomUUID().replace(/-/g, "") + randomUUID().replace(/-/g, "").slice(0, 12);
}
