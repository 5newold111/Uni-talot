"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2, Check } from "lucide-react";
import { saveTransactionsBatchAction } from "@/app/actions";
import {
  TAX_CATEGORIES,
  type TaxCategory,
  type TxKind,
} from "@/lib/constants";
import { taxFromGross } from "@/lib/accounting";
import { formatYen, todayIso } from "@/lib/format";
import type { Account, Partner } from "@/lib/types";

interface PendingEntry {
  key: string;
  kind: "EXPENSE" | "INCOME";
  date: string;
  description: string;
  partnerId: string;
  mainAccountId: string;
  counterAccountId: string;
  amount: number;
  taxCategory: TaxCategory;
}

let counter = 0;

export function QuickEntry({
  accounts,
  partners,
}: {
  accounts: Account[];
  partners: Partner[];
}) {
  const router = useRouter();
  const expenseAccounts = accounts.filter((a) => a.type === "EXPENSE");
  const revenueAccounts = accounts.filter((a) => a.type === "REVENUE");
  const paymentAccounts = accounts.filter(
    (a) => a.type === "ASSET" || a.type === "LIABILITY",
  );
  const accName = useMemo(
    () => new Map(accounts.map((a) => [a.id, a.name])),
    [accounts],
  );
  const byCode = (code: string) => accounts.find((a) => a.code === code)?.id ?? "";

  const [kind, setKind] = useState<"EXPENSE" | "INCOME">("EXPENSE");
  const [date, setDate] = useState(todayIso());
  const [amount, setAmount] = useState<number>(0);
  const [description, setDescription] = useState("");
  const [partnerId, setPartnerId] = useState("");
  const [taxCategory, setTaxCategory] = useState<TaxCategory>("TAXABLE_10");
  const [expenseAccountId, setExpenseAccountId] = useState(expenseAccounts[0]?.id ?? "");
  const [revenueAccountId, setRevenueAccountId] = useState(byCode("401") || revenueAccounts[0]?.id || "");
  const [expensePayId, setExpensePayId] = useState(byCode("101") || paymentAccounts[0]?.id || "");
  const [incomePayId, setIncomePayId] = useState(byCode("111") || paymentAccounts[0]?.id || "");

  const [pending, setPending] = useState<PendingEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedCount, setSavedCount] = useState<number | null>(null);

  const innerTax = amount > 0 ? taxFromGross(amount, taxCategory) : 0;

  function addToList() {
    setError(null);
    if (amount <= 0) {
      setError("金額を入力してください");
      return;
    }
    const entry: PendingEntry = {
      key: `e${counter++}`,
      kind,
      date,
      description: description.trim() || (kind === "EXPENSE" ? "経費" : "売上"),
      partnerId,
      mainAccountId: kind === "EXPENSE" ? expenseAccountId : revenueAccountId,
      counterAccountId: kind === "EXPENSE" ? expensePayId : incomePayId,
      amount,
      taxCategory,
    };
    setPending((p) => [...p, entry]);
    // 次の入力のため金額と摘要をリセット（日付・科目は保持）
    setAmount(0);
    setDescription("");
    setSavedCount(null);
  }

  function remove(key: string) {
    setPending((p) => p.filter((e) => e.key !== key));
  }

  async function saveAll() {
    if (pending.length === 0) return;
    setBusy(true);
    setError(null);
    const inputs = pending.map((e) => {
      const lines =
        e.kind === "EXPENSE"
          ? [
              { accountId: e.mainAccountId, side: "DEBIT" as const, amount: e.amount, taxCategory: e.taxCategory },
              { accountId: e.counterAccountId, side: "CREDIT" as const, amount: e.amount, taxCategory: "OUT_OF_SCOPE" as const },
            ]
          : [
              { accountId: e.counterAccountId, side: "DEBIT" as const, amount: e.amount, taxCategory: "OUT_OF_SCOPE" as const },
              { accountId: e.mainAccountId, side: "CREDIT" as const, amount: e.amount, taxCategory: e.taxCategory },
            ];
      return {
        date: e.date,
        description: e.description,
        partnerId: e.partnerId || null,
        kind: e.kind as TxKind,
        lines,
      };
    });
    const res = await saveTransactionsBatchAction(inputs);
    setBusy(false);
    if (res.ok) {
      setSavedCount(res.count ?? pending.length);
      setPending([]);
      router.refresh();
    } else {
      setError(res.error);
    }
  }

  const total = pending.reduce((s, e) => s + e.amount, 0);
  const mainAccounts = kind === "EXPENSE" ? expenseAccounts : revenueAccounts;
  const mainId = kind === "EXPENSE" ? expenseAccountId : revenueAccountId;
  const setMainId = kind === "EXPENSE" ? setExpenseAccountId : setRevenueAccountId;
  const payId = kind === "EXPENSE" ? expensePayId : incomePayId;
  const setPayId = kind === "EXPENSE" ? setExpensePayId : setIncomePayId;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* 入力フォーム */}
      <div className="card p-5">
        {/* 経費/売上 切替（大きめ） */}
        <div className="mb-4 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setKind("EXPENSE")}
            className={`rounded-xl py-3 text-base font-bold transition-colors ${
              kind === "EXPENSE" ? "bg-amber-500 text-white" : "bg-slate-100 text-slate-500"
            }`}
          >
            経費を記録
          </button>
          <button
            type="button"
            onClick={() => setKind("INCOME")}
            className={`rounded-xl py-3 text-base font-bold transition-colors ${
              kind === "INCOME" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-500"
            }`}
          >
            売上を記録
          </button>
        </div>

        {/* 金額（大） */}
        <div className="mb-4">
          <label className="label">金額（税込）</label>
          <div className="flex items-center rounded-xl border border-slate-300 px-4 focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-100">
            <span className="text-2xl font-bold text-slate-400">¥</span>
            <input
              type="number"
              inputMode="numeric"
              className="w-full bg-transparent py-3 text-right text-3xl font-bold tabular-nums outline-none"
              value={amount || ""}
              placeholder="0"
              onChange={(e) => setAmount(Number(e.target.value))}
            />
          </div>
          <p className="mt-1 text-right text-xs text-slate-400">うち消費税 {formatYen(innerTax)}</p>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="label">日付</label>
            <input type="date" className="input py-3" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div>
            <label className="label">{kind === "EXPENSE" ? "勘定科目（経費）" : "勘定科目（売上）"}</label>
            <select className="input py-3" value={mainId} onChange={(e) => setMainId(e.target.value)}>
              {mainAccounts.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">{kind === "EXPENSE" ? "支払方法" : "入金先"}</label>
            <select className="input py-3" value={payId} onChange={(e) => setPayId(e.target.value)}>
              {paymentAccounts.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">消費税区分</label>
            <select className="input py-3" value={taxCategory} onChange={(e) => setTaxCategory(e.target.value as TaxCategory)}>
              {Object.entries(TAX_CATEGORIES).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="label">摘要（任意）</label>
            <input className="input py-3" value={description} placeholder="例: コンビニ / ◯月分 売上" onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div className="sm:col-span-2">
            <label className="label">取引先（任意）</label>
            <select className="input py-3" value={partnerId} onChange={(e) => setPartnerId(e.target.value)}>
              <option value="">—</option>
              {partners.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        </div>

        {error && <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}

        <button type="button" className="btn-primary mt-4 w-full py-3 text-base" onClick={addToList}>
          <Plus size={18} /> リストに追加
        </button>
      </div>

      {/* 入力リスト */}
      <div className="card flex flex-col p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-700">入力リスト（{pending.length}件）</h2>
          {savedCount !== null && (
            <span className="flex items-center gap-1 text-sm text-emerald-600">
              <Check size={16} /> {savedCount}件を保存しました
            </span>
          )}
        </div>

        {pending.length === 0 ? (
          <div className="flex flex-1 items-center justify-center py-12 text-center text-sm text-slate-400">
            左で入力して「リストに追加」を押すと、ここに溜まります。<br />
            まとめて保存できます。
          </div>
        ) : (
          <div className="flex-1 space-y-2 overflow-y-auto">
            {pending.map((e) => (
              <div key={e.key} className="flex items-center gap-3 rounded-lg border border-slate-100 px-3 py-2">
                <span className={`badge ${e.kind === "EXPENSE" ? "bg-amber-50 text-amber-700" : "bg-brand-50 text-brand-700"}`}>
                  {e.kind === "EXPENSE" ? "経費" : "売上"}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{e.description}</div>
                  <div className="truncate text-xs text-slate-400">
                    {e.date} ・ {accName.get(e.mainAccountId)}
                  </div>
                </div>
                <div className="text-right text-sm font-semibold tabular-nums">{formatYen(e.amount)}</div>
                <button type="button" className="text-slate-300 hover:text-red-500" onClick={() => remove(e.key)}>
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="mt-4 border-t border-slate-100 pt-4">
          <div className="mb-3 flex justify-between text-sm">
            <span className="text-slate-500">合計</span>
            <span className="font-bold tabular-nums">{formatYen(total)}</span>
          </div>
          <button
            type="button"
            className="btn-primary w-full py-3 text-base"
            disabled={busy || pending.length === 0}
            onClick={saveAll}
          >
            {busy ? "保存中…" : `${pending.length}件をまとめて保存`}
          </button>
        </div>
      </div>
    </div>
  );
}
