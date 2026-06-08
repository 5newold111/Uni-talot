"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Receipt } from "lucide-react";
import { loginAction, registerAction } from "@/app/actions";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    setBusy(true);
    const res =
      mode === "login"
        ? await loginAction({ email, password })
        : await registerAction({ email, password, name, businessName });
    setBusy(false);
    if (res.ok) {
      router.push("/");
      router.refresh();
    } else {
      setError(res.error);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-white">
            <Receipt size={24} />
          </div>
          <h1 className="mt-3 text-lg font-bold">会計フリー帳</h1>
          <p className="text-xs text-slate-400">個人事業主の財務管理</p>
        </div>

        <div className="card p-6">
          <h2 className="mb-4 text-base font-bold">
            {mode === "login" ? "ログイン" : "新規登録"}
          </h2>
          <div className="space-y-3">
            {mode === "register" && (
              <>
                <div>
                  <label className="label">氏名</label>
                  <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
                </div>
                <div>
                  <label className="label">屋号（任意）</label>
                  <input className="input" value={businessName} onChange={(e) => setBusinessName(e.target.value)} />
                </div>
              </>
            )}
            <div>
              <label className="label">メールアドレス</label>
              <input
                type="email"
                className="input"
                value={email}
                autoComplete="email"
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit()}
              />
            </div>
            <div>
              <label className="label">パスワード{mode === "register" && "（8文字以上）"}</label>
              <input
                type="password"
                className="input"
                value={password}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit()}
              />
            </div>
          </div>

          {error && <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}

          <button className="btn-primary mt-5 w-full" onClick={submit} disabled={busy}>
            {busy ? "処理中…" : mode === "login" ? "ログイン" : "登録して始める"}
          </button>

          <div className="mt-4 text-center text-sm text-slate-500">
            {mode === "login" ? (
              <>
                アカウントが無い方は{" "}
                <Link href="/register" className="font-medium text-brand-600 hover:underline">新規登録</Link>
              </>
            ) : (
              <>
                既にお持ちの方は{" "}
                <Link href="/login" className="font-medium text-brand-600 hover:underline">ログイン</Link>
              </>
            )}
          </div>
        </div>

        {mode === "login" && (
          <div className="mt-4 rounded-lg border border-dashed border-slate-300 bg-white px-4 py-3 text-xs text-slate-500">
            <div className="font-medium text-slate-600">デモアカウント</div>
            <div>メール: demo@example.com ／ パスワード: demo1234</div>
          </div>
        )}
      </div>
    </div>
  );
}
