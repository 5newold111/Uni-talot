// セッションCookieの読み書き（Next.js のサーバーサイド専用）。
import { cookies } from "next/headers";
import {
  SESSION_COOKIE,
  SESSION_MAX_AGE,
  createSessionToken,
  verifySessionToken,
} from "./auth";

/** 現在のログインユーザーID。未ログインなら null。 */
export function getSessionUserId(): string | null {
  const token = cookies().get(SESSION_COOKIE)?.value;
  return verifySessionToken(token);
}

/** ログイン（Server Action / Route Handler 内でのみ呼べる）。 */
export function setSessionCookie(userId: string): void {
  cookies().set(SESSION_COOKIE, createSessionToken(userId), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE,
    secure: process.env.NODE_ENV === "production",
  });
}

export function clearSessionCookie(): void {
  cookies().delete(SESSION_COOKIE);
}
