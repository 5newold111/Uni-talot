"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { savePartnerAction, deletePartnerAction } from "@/app/actions";
import { PARTNER_TYPES, type PartnerType } from "@/lib/constants";
import type { Partner } from "@/lib/types";

export function PartnersManager({ partners }: { partners: Partner[] }) {
  const router = useRouter();
  const [editing, setEditing] = useState<Partner | "new" | null>(null);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button className="btn-primary" onClick={() => setEditing("new")}>
          <Plus size={16} /> 取引先を追加
        </button>
      </div>

      {partners.length === 0 ? (
        <div className="card px-6 py-16 text-center text-sm text-slate-400">
          取引先が登録されていません
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="border-b border-slate-100 bg-slate-50/60">
              <tr>
                <th className="th">名称</th>
                <th className="th">区分</th>
                <th className="th">インボイス番号</th>
                <th className="th">連絡先</th>
                <th className="th" />
              </tr>
            </thead>
            <tbody>
              {partners.map((p) => (
                <tr key={p.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/50">
                  <td className="td font-medium">{p.name}</td>
                  <td className="td text-xs text-slate-500">{PARTNER_TYPES[p.type]}</td>
                  <td className="td text-xs tabular-nums text-slate-500">
                    {p.invoiceNumber || <span className="text-amber-500">未登録</span>}
                  </td>
                  <td className="td text-xs text-slate-400">{p.email || p.phone || ""}</td>
                  <td className="td text-right">
                    <div className="flex justify-end gap-2">
                      <button onClick={() => setEditing(p)} className="text-slate-400 hover:text-brand-600">
                        <Pencil size={15} />
                      </button>
                      <DeleteButton id={p.id} onDone={() => router.refresh()} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <PartnerModal
          partner={editing === "new" ? null : editing}
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
        if (!confirm("この取引先を削除しますか？")) return;
        setBusy(true);
        const res = await deletePartnerAction(id);
        setBusy(false);
        if (!res.ok) alert(res.error);
        else onDone();
      }}
    >
      <Trash2 size={15} />
    </button>
  );
}

function PartnerModal({
  partner,
  onClose,
  onSaved,
}: {
  partner: Partner | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(partner?.name ?? "");
  const [type, setType] = useState<PartnerType>(partner?.type ?? "BOTH");
  const [invoiceNumber, setInvoiceNumber] = useState(partner?.invoiceNumber ?? "");
  const [email, setEmail] = useState(partner?.email ?? "");
  const [phone, setPhone] = useState(partner?.phone ?? "");
  const [address, setAddress] = useState(partner?.address ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!name.trim()) {
      setError("名称は必須です");
      return;
    }
    setBusy(true);
    const res = await savePartnerAction(
      { name: name.trim(), type, invoiceNumber, email, phone, address },
      partner?.id,
    );
    setBusy(false);
    if (res.ok) onSaved();
    else setError(res.error);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <div className="card w-full max-w-md p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-4 text-base font-bold">{partner ? "取引先を編集" : "取引先を追加"}</h3>
        <div className="space-y-3">
          <div>
            <label className="label">名称</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">区分</label>
              <select className="input" value={type} onChange={(e) => setType(e.target.value as PartnerType)}>
                {Object.entries(PARTNER_TYPES).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">インボイス番号</label>
              <input className="input" placeholder="T1234567890123" value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">メール</label>
              <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="label">電話</label>
              <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="label">住所</label>
            <input className="input" value={address} onChange={(e) => setAddress(e.target.value)} />
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
