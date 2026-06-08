// 認証ユーティリティ。外部依存を増やさず node:crypto で実装する。
// - パスワードは scrypt でハッシュ（"salt:hash"）
// - セッションは HMAC 署名付きCookie（payload.signature）
import {
  createHmac,
  randomBytes,
  scryptSync,
  timingSafeEqual,
} from "node:crypto";

export const SESSION_COOKIE = "kaikei_session";
const SESSION_TTL_SEC = 60 * 60 * 24 * 30; // 30日

function secret(): string {
  return process.env.AUTH_SECRET || "dev-insecure-secret-change-me";
}

// ---------------- password ----------------
export function hashPassword(password: string): string {
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(password, salt, 64).toString("hex");
  return `${salt}:${hash}`;
}

export function verifyPassword(password: string, stored?: string): boolean {
  if (!stored || !stored.includes(":")) return false;
  const [salt, hash] = stored.split(":");
  const expected = Buffer.from(hash, "hex");
  const actual = scryptSync(password, salt, 64);
  if (expected.length !== actual.length) return false;
  return timingSafeEqual(expected, actual);
}

// ---------------- session token ----------------
function sign(data: string): string {
  return createHmac("sha256", secret()).update(data).digest("base64url");
}

export function createSessionToken(userId: string): string {
  const payload = {
    uid: userId,
    exp: Math.floor(Date.now() / 1000) + SESSION_TTL_SEC,
  };
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${body}.${sign(body)}`;
}

export function verifySessionToken(token: string | undefined): string | null {
  if (!token || !token.includes(".")) return null;
  const [body, sig] = token.split(".");
  const expected = sign(body);
  if (
    sig.length !== expected.length ||
    !timingSafeEqual(Buffer.from(sig), Buffer.from(expected))
  ) {
    return null;
  }
  try {
    const payload = JSON.parse(Buffer.from(body, "base64url").toString());
    if (typeof payload.exp === "number" && payload.exp < Date.now() / 1000) {
      return null;
    }
    return typeof payload.uid === "string" ? payload.uid : null;
  } catch {
    return null;
  }
}

export const SESSION_MAX_AGE = SESSION_TTL_SEC;
