"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { saveAccountAction, deleteAccountAction } from "@/app/actions";
import {
  ACCOUNT_TYPES,
  TAX_CATEGORIES,
  type AccountType,
  type TaxCategory,
} from "@/lib/constants";
import type { Account } from "@/lib/types";

export function AccountsManager({ accounts }: { accounts: Account[] }) {
  const router = useRouter();
  const [editing, setEditing] = useState<Account | "new" | null>(null);

  const grouped = (Object.keys(ACCOUNT_TYPES) as AccountType[]).map((type) => ({
    type,
    items: accounts.filter((a) => a.type === type),
  }));

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button className="btn-primary" onClick={() => setEditing("new")}>
          <Plus size={16} /> 科目を追加
        </button>
      </div>

      {grouped.map(({ type, items }) => (
        <div key={type} className="card overflow-hidden">
          <div className="border-b border-slate-100 bg-slate-50/60 px-4 py-2 text-sm font-semibold text-slate-600">
            {ACCOUNT_TYPES[type]}（{items.length}）
          </div>
          <table className="w-full">
            <tbody>
              {items.map((a) => (
                <tr key={a.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/50">
                  <td className="td w-20 tabular-nums text-slate-400">{a.code}</td>
                  <td className="td font-medium">{a.name}</td>
                  <td className="td text-xs text-slate-400">
                    {a.defaultTaxCategory ? TAX_CATEGORIES[a.defaultTaxCategory] : ""}
                  </td>
                  <td className="td text-right">
                    {a.isSystem ? (
                      <span className="badge bg-slate-100 text-slate-400">標準</span>
                    ) : (
                      <div className="flex justify-end gap-2">
                        <button onClick={() => setEditing(a)} className="text-slate-400 hover:text-brand-600">
                          <Pencil size={15} />
                        </button>
                        <DeleteButton id={a.id} onDone={() => router.refresh()} />
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {editing && (
        <AccountModal
          account={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            router.refresh();
          }}
        />
      )}
    </div>
  );
}

function DeleteButton({ id, onDone }: { id: string; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      className="text-slate-400 hover:text-red-500"
      disabled={busy}
      onClick={async () => {
        if (!confirm("この科目を削除しますか？")) return;
        setBusy(true);
        const res = await deleteAccountAction(id);
        setBusy(false);
        if (!res.ok) alert(res.error);
        else onDone();
      }}
    >
      <Trash2 size={15} />
    </button>
  );
}

function AccountModal({
  account,
  onClose,
  onSaved,
}: {
  account: Account | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [code, setCode] = useState(account?.code ?? "");
  const [name, setName] = useState(account?.name ?? "");
  const [type, setType] = useState<AccountType>(account?.type ?? "EXPENSE");
  const [tax, setTax] = useState<TaxCategory | "">(account?.defaultTaxCategory ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!code.trim() || !name.trim()) {
      setError("コードと名称は必須です");
      return;
    }
    setBusy(true);
    const res = await saveAccountAction(
      {
        code: code.trim(),
        name: name.trim(),
        type,
        defaultTaxCategory: tax || null,
        isActive: true,
      },
      account?.id,
    );
    setBusy(false);
    if (res.ok) onSaved();
    else setError(res.error);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <div className="card w-full max-w-md p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-4 text-base font-bold">{account ? "科目を編集" : "科目を追加"}</h3>
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="label">コード</label>
              <input className="input" value={code} onChange={(e) => setCode(e.target.value)} />
            </div>
            <div className="col-span-2">
              <label className="label">名称</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="label">区分</label>
            <select className="input" value={type} onChange={(e) => setType(e.target.value as AccountType)}>
              {Object.entries(ACCOUNT_TYPES).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">既定の消費税区分</label>
            <select className="input" value={tax} onChange={(e) => setTax(e.target.value as TaxCategory | "")}>
              <option value="">指定なし</option>
              {Object.entries(TAX_CATEGORIES).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
        </div>
        {error && <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
        <div className="mt-5 flex justify-end gap-2">
          <button className="btn-secondary" onClick={onClose} disabled={busy}>キャンセル</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? "保存中…" : "保存"}</button>
        </div>
      </div>
    </div>
  );
}
