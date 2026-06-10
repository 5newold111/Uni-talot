"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2 } from "lucide-react";
import { saveInvoiceAction, deleteInvoiceAction } from "@/app/actions";
import { summarizeInvoiceItems } from "@/lib/accounting";
import {
  INVOICE_STATUS,
  TAX_CATEGORIES,
  type InvoiceStatus,
  type TaxCategory,
} from "@/lib/constants";
import { formatYen, todayIso } from "@/lib/format";
import type { InvoiceWithItems, Partner } from "@/lib/types";

interface Props {
  partners: Partner[];
  defaultNumber: string;
  initial?: InvoiceWithItems;
}

interface ItemState {
  key: string;
  description: string;
  quantity: number;
  unitPrice: number;
  taxCategory: TaxCategory;
}

let k = 0;
const nk = () => `it${k++}`;

export function InvoiceForm({ partners, defaultNumber, initial }: Props) {
  const router = useRouter();
  const [number, setNumber] = useState(initial?.number ?? defaultNumber);
  const [partnerId, setPartnerId] = useState(initial?.partnerId ?? "");
  const [issueDate, setIssueDate] = useState(initial?.issueDate ?? todayIso());
  const [dueDate, setDueDate] = useState(initial?.dueDate ?? "");
  const [status, setStatus] = useState<InvoiceStatus>(initial?.status ?? "DRAFT");
  const [note, setNote] = useState(initial?.note ?? "");
  const [items, setItems] = useState<ItemState[]>(
    initial
      ? initial.items.map((it) => ({
          key: nk(),
          description: it.description,
          quantity: it.quantity,
          unitPrice: it.unitPrice,
          taxCategory: it.taxCategory,
        }))
      : [{ key: nk(), description: "", quantity: 1, unitPrice: 0, taxCategory: "TAXABLE_10" }],
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const summary = useMemo(
    () => summarizeInvoiceItems(items.map((i) => ({ quantity: i.quantity, unitPrice: i.unitPrice, taxCategory: i.taxCategory }))),
    [items],
  );

  const update = (key: string, patch: Partial<ItemState>) =>
    setItems(items.map((it) => (it.key === key ? { ...it, ...patch } : it)));
  const add = () => setItems([...items, { key: nk(), description: "", quantity: 1, unitPrice: 0, taxCategory: "TAXABLE_10" }]);
  const remove = (key: string) => setItems(items.filter((it) => it.key !== key));

  async function save() {
    setError(null);
    if (!number.trim()) return setError("請求書番号を入力してください");
    const valid = items.filter((i) => i.description.trim() && i.unitPrice > 0);
    if (valid.length === 0) return setError("明細を1行以上入力してください");
    setBusy(true);
    const res = await saveInvoiceAction(
      {
        number: number.trim(),
        partnerId: partnerId || null,
        issueDate,
        dueDate: dueDate || null,
        status,
        note,
        items: valid.map((i) => ({
          description: i.description.trim(),
          quantity: i.quantity,
          unitPrice: i.unitPrice,
          taxCategory: i.taxCategory,
        })),
      },
      initial?.id,
    );
    setBusy(false);
    if (res.ok) router.push("/invoices");
    else setError(res.error);
  }

  async function onDelete() {
    if (!initial) return;
    if (!confirm("この請求書を削除しますか？")) return;
    setBusy(true);
    const res = await deleteInvoiceAction(initial.id);
    setBusy(false);
    if (res.ok) router.push("/invoices");
    else setError(res.error);
  }

  return (
    <div className="space-y-5">
      <div className="card p-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="label">請求書番号</label>
            <input className="input" value={number} onChange={(e) => setNumber(e.target.value)} />
          </div>
          <div>
            <label className="label">取引先</label>
            <select className="input" value={partnerId} onChange={(e) => setPartnerId(e.target.value)}>
              <option value="">—</option>
              {partners.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">発行日</label>
            <input type="date" className="input" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
          </div>
          <div>
            <label className="label">支払期限</label>
            <input type="date" className="input" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </div>
          <div>
            <label className="label">ステータス</label>
            <select className="input" value={status} onChange={(e) => setStatus(e.target.value as InvoiceStatus)}>
              {Object.entries(INVOICE_STATUS).map(([key, v]) => (
                <option key={key} value={key}>{v}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="card p-5">
        <div className="mb-2 grid grid-cols-12 gap-2 text-xs font-medium text-slate-400">
          <div className="col-span-5">品目・摘要</div>
          <div className="col-span-1 text-right">数量</div>
          <div className="col-span-2 text-right">単価（税抜）</div>
          <div className="col-span-2">税区分</div>
          <div className="col-span-1 text-right">金額</div>
          <div className="col-span-1" />
        </div>
        <div className="space-y-2">
          {items.map((it) => (
            <div key={it.key} className="grid grid-cols-12 items-center gap-2">
              <input className="input col-span-5" placeholder="品目名" value={it.description} onChange={(e) => update(it.key, { description: e.target.value })} />
              <input type="number" className="input col-span-1 px-1 text-right" value={it.quantity || ""} onChange={(e) => update(it.key, { quantity: Number(e.target.value) })} />
              <input type="number" className="input col-span-2 text-right" value={it.unitPrice || ""} onChange={(e) => update(it.key, { unitPrice: Number(e.target.value) })} />
              <select className="input col-span-2 px-1" value={it.taxCategory} onChange={(e) => update(it.key, { taxCategory: e.target.value as TaxCategory })}>
                {Object.entries(TAX_CATEGORIES).map(([key, v]) => (
                  <option key={key} value={key}>{v}</option>
                ))}
              </select>
              <div className="col-span-1 text-right text-sm tabular-nums text-slate-500">{formatYen(it.quantity * it.unitPrice)}</div>
              <button type="button" className="col-span-1 flex justify-center text-slate-400 hover:text-red-500" onClick={() => remove(it.key)}>
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
        <button type="button" className="btn-secondary mt-3 text-xs" onClick={add}>
          <Plus size={14} /> 明細を追加
        </button>

        <div className="mt-4 flex justify-end">
          <div className="w-64 space-y-1 text-sm">
            <div className="flex justify-between"><span className="text-slate-500">小計（税抜）</span><span className="tabular-nums">{formatYen(summary.subtotal)}</span></div>
            {summary.rows.filter((r) => r.rate > 0).map((r) => (
              <div key={r.taxCategory} className="flex justify-between text-xs text-slate-400">
                <span>消費税（{r.rate}%対象 {formatYen(r.net)}）</span><span className="tabular-nums">{formatYen(r.tax)}</span>
              </div>
            ))}
            <div className="flex justify-between border-t border-slate-200 pt-1 text-base font-bold">
              <span>合計</span><span className="tabular-nums">{formatYen(summary.total)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="card p-5">
        <label className="label">備考</label>
        <textarea className="input" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
      </div>

      {error && <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</div>}

      <div className="flex items-center justify-between">
        <div>
          {initial && (
            <button type="button" className="btn-danger" onClick={onDelete} disabled={busy}>
              <Trash2 size={16} /> 削除
            </button>
          )}
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn-secondary" onClick={() => router.back()} disabled={busy}>キャンセル</button>
          <button type="button" className="btn-primary" onClick={save} disabled={busy}>{busy ? "保存中…" : "保存"}</button>
        </div>
      </div>
    </div>
  );
}
