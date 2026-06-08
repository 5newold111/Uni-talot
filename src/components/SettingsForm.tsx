"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { saveSettingsAction } from "@/app/actions";
import {
  CONSUMPTION_TAX_METHOD,
  CONSUMPTION_TAX_STATUS,
  TAXATION_TYPES,
  TAX_ROUNDING,
  type ConsumptionTaxMethod,
  type ConsumptionTaxStatus,
  type TaxationType,
  type TaxRounding,
} from "@/lib/constants";
import type { User } from "@/lib/types";

export function SettingsForm({ user }: { user: User }) {
  const router = useRouter();
  const [f, setF] = useState({
    name: user.name,
    businessName: user.businessName ?? "",
    email: user.email,
    invoiceNumber: user.invoiceNumber ?? "",
    taxationType: user.taxationType as TaxationType,
    consumptionTaxStatus: user.consumptionTaxStatus as ConsumptionTaxStatus,
    consumptionTaxMethod: user.consumptionTaxMethod as ConsumptionTaxMethod,
    taxRounding: user.taxRounding as TaxRounding,
    fiscalYearStartMonth: user.fiscalYearStartMonth,
  });
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => {
    setF({ ...f, [k]: v });
    setSaved(false);
  };

  async function save() {
    setBusy(true);
    setError(null);
    const res = await saveSettingsAction(f);
    setBusy(false);
    if (res.ok) {
      setSaved(true);
      router.refresh();
    } else setError(res.error);
  }

  return (
    <div className="space-y-6">
      <section className="card p-5">
        <h2 className="mb-4 text-sm font-bold text-slate-700">事業者情報</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="label">氏名</label>
            <input className="input" value={f.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div>
            <label className="label">屋号</label>
            <input className="input" value={f.businessName} onChange={(e) => set("businessName", e.target.value)} />
          </div>
          <div>
            <label className="label">メールアドレス</label>
            <input className="input" value={f.email} onChange={(e) => set("email", e.target.value)} />
          </div>
          <div>
            <label className="label">適格請求書発行事業者 登録番号（インボイス番号）</label>
            <input className="input" placeholder="T1234567890123" value={f.invoiceNumber} onChange={(e) => set("invoiceNumber", e.target.value)} />
          </div>
        </div>
      </section>

      <section className="card p-5">
        <h2 className="mb-4 text-sm font-bold text-slate-700">申告・税設定</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="label">申告方式</label>
            <select className="input" value={f.taxationType} onChange={(e) => set("taxationType", e.target.value as TaxationType)}>
              {Object.entries(TAXATION_TYPES).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">消費税の納税義務</label>
            <select className="input" value={f.consumptionTaxStatus} onChange={(e) => set("consumptionTaxStatus", e.target.value as ConsumptionTaxStatus)}>
              {Object.entries(CONSUMPTION_TAX_STATUS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">消費税の計算方式</label>
            <select className="input" value={f.consumptionTaxMethod} onChange={(e) => set("consumptionTaxMethod", e.target.value as ConsumptionTaxMethod)}>
              {Object.entries(CONSUMPTION_TAX_METHOD).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">消費税の端数処理</label>
            <select className="input" value={f.taxRounding} onChange={(e) => set("taxRounding", e.target.value as TaxRounding)}>
              {Object.entries(TAX_ROUNDING).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {error && <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</div>}

      <div className="flex items-center justify-end gap-3">
        {saved && <span className="text-sm text-emerald-600">保存しました ✓</span>}
        <button className="btn-primary" onClick={save} disabled={busy}>
          {busy ? "保存中…" : "設定を保存"}
        </button>
      </div>
    </div>
  );
}
