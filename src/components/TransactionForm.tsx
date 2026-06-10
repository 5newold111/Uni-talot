"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2 } from "lucide-react";
import { saveTransactionAction, deleteTransactionAction } from "@/app/actions";
import {
  TAX_CATEGORIES,
  type TaxCategory,
  type TxKind,
} from "@/lib/constants";
import { taxFromGross } from "@/lib/accounting";
import { formatYen, todayIso } from "@/lib/format";
import { ReceiptScanner, type ScanResult } from "@/components/ReceiptScanner";
import type { AttachmentInput } from "@/lib/repo";
import type { Account, Partner, TransactionWithLines } from "@/lib/types";

interface Props {
  accounts: Account[];
  partners: Partner[];
  initial?: TransactionWithLines;
}

interface LineState {
  key: string;
  accountId: string;
  side: "DEBIT" | "CREDIT";
  amount: number;
  taxCategory: TaxCategory;
}

const MODES: { key: TxKind; label: string }[] = [
  { key: "EXPENSE", label: "経費" },
  { key: "INCOME", label: "売上" },
  { key: "TRANSFER", label: "振替" },
  { key: "JOURNAL", label: "仕訳（詳細）" },
];

let keyCounter = 0;
const newKey = () => `l${keyCounter++}`;

export function TransactionForm({ accounts, partners, initial }: Props) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const expenseAccounts = accounts.filter((a) => a.type === "EXPENSE");
  const revenueAccounts = accounts.filter((a) => a.type === "REVENUE");
  const paymentAccounts = accounts.filter(
    (a) => a.type === "ASSET" || a.type === "LIABILITY",
  );

  const initialMode: TxKind =
    initial?.kind && initial.lines.length === 2 ? initial.kind : initial ? "JOURNAL" : "EXPENSE";

  const [mode, setMode] = useState<TxKind>(initialMode);
  const [date, setDate] = useState(initial?.date ?? todayIso());
  const [description, setDescription] = useState(initial?.description ?? "");
  const [partnerId, setPartnerId] = useState(initial?.partnerId ?? "");
  const [note, setNote] = useState(initial?.note ?? "");
  const [attachments, setAttachments] = useState<AttachmentInput[]>([]);

  function onScan(r: ScanResult) {
    if (r.amount != null && r.amount > 0) setAmount(r.amount);
    if (r.date) setDate(r.date);
    if (!description.trim()) setDescription(r.fileName.replace(/\.[^.]+$/, ""));
    setAttachments((prev) => [
      ...prev,
      { fileName: r.fileName, mimeType: r.mimeType, dataUrl: r.dataUrl, ocrText: r.ocrText },
    ]);
  }

  // --- simple mode (2-line) state ---
  const detectSimple = () => {
    if (!initial || initial.lines.length !== 2) return null;
    const debit = initial.lines.find((l) => l.side === "DEBIT")!;
    const credit = initial.lines.find((l) => l.side === "CREDIT")!;
    return { debit, credit };
  };
  const simple = detectSimple();

  const [mainAccountId, setMainAccountId] = useState(
    initialMode === "INCOME"
      ? simple?.credit.accountId ?? revenueAccounts[0]?.id ?? ""
      : simple?.debit.accountId ?? expenseAccounts[0]?.id ?? "",
  );
  const [counterAccountId, setCounterAccountId] = useState(
    initialMode === "INCOME"
      ? simple?.debit.accountId ?? paymentAccounts.find((a) => a.code === "111")?.id ?? paymentAccounts[0]?.id ?? ""
      : simple?.credit.accountId ?? paymentAccounts.find((a) => a.code === "101")?.id ?? paymentAccounts[0]?.id ?? "",
  );
  const [amount, setAmount] = useState<number>(
    simple ? simple.debit.amount : 0,
  );
  const [taxCategory, setTaxCategory] = useState<TaxCategory>(
    (initialMode === "INCOME" ? simple?.credit.taxCategory : simple?.debit.taxCategory) ??
      "TAXABLE_10",
  );

  // --- journal mode state ---
  const [lines, setLines] = useState<LineState[]>(
    initial && initialMode === "JOURNAL"
      ? initial.lines.map((l) => ({
          key: newKey(),
          accountId: l.accountId,
          side: l.side,
          amount: l.amount,
          taxCategory: l.taxCategory,
        }))
      : [
          { key: newKey(), accountId: accounts[0]?.id ?? "", side: "DEBIT", amount: 0, taxCategory: "TAXABLE_10" },
          { key: newKey(), accountId: accounts[0]?.id ?? "", side: "CREDIT", amount: 0, taxCategory: "OUT_OF_SCOPE" },
        ],
  );

  const debitSum = lines.filter((l) => l.side === "DEBIT").reduce((s, l) => s + (l.amount || 0), 0);
  const creditSum = lines.filter((l) => l.side === "CREDIT").reduce((s, l) => s + (l.amount || 0), 0);
  const balanced = debitSum === creditSum && debitSum > 0;

  const innerTax = useMemo(
    () => (mode === "EXPENSE" || mode === "INCOME" ? taxFromGross(amount, taxCategory) : 0),
    [mode, amount, taxCategory],
  );

  function buildPayload(): { date: string; description: string; partnerId: string | null; kind: TxKind; note: string; lines: { accountId: string; side: "DEBIT" | "CREDIT"; amount: number; taxCategory: TaxCategory }[] } | null {
    if (!date || !description.trim()) {
      setError("日付と摘要を入力してください");
      return null;
    }
    if (mode === "JOURNAL") {
      if (!balanced) {
        setError("借方と貸方の合計が一致していません");
        return null;
      }
      return {
        date,
        description: description.trim(),
        partnerId: partnerId || null,
        kind: "JOURNAL",
        note,
        lines: lines
          .filter((l) => l.accountId && l.amount > 0)
          .map((l) => ({ accountId: l.accountId, side: l.side, amount: Math.round(l.amount), taxCategory: l.taxCategory })),
      };
    }
    if (amount <= 0) {
      setError("金額を入力してください");
      return null;
    }
    // simple modes
    if (mode === "EXPENSE") {
      // 借方: 費用科目(課税区分) / 貸方: 支払科目
      return {
        date, description: description.trim(), partnerId: partnerId || null, kind: "EXPENSE", note,
        lines: [
          { accountId: mainAccountId, side: "DEBIT", amount, taxCategory },
          { accountId: counterAccountId, side: "CREDIT", amount, taxCategory: "OUT_OF_SCOPE" },
        ],
      };
    }
    if (mode === "INCOME") {
      // 借方: 入金科目 / 貸方: 収益科目(課税区分)
      return {
        date, description: description.trim(), partnerId: partnerId || null, kind: "INCOME", note,
        lines: [
          { accountId: counterAccountId, side: "DEBIT", amount, taxCategory: "OUT_OF_SCOPE" },
          { accountId: mainAccountId, side: "CREDIT", amount, taxCategory },
        ],
      };
    }
    // TRANSFER: 借方 振替先 / 貸方 振替元（不課税）
    return {
      date, description: description.trim(), partnerId: partnerId || null, kind: "TRANSFER", note,
      lines: [
        { accountId: mainAccountId, side: "DEBIT", amount, taxCategory: "OUT_OF_SCOPE" },
        { accountId: counterAccountId, side: "CREDIT", amount, taxCategory: "OUT_OF_SCOPE" },
      ],
    };
  }

  async function onSubmit() {
    setError(null);
    const payload = buildPayload();
    if (!payload) return;
    setSaving(true);
    const res = await saveTransactionAction(
      { ...payload, attachments },
      initial?.id,
    );
    setSaving(false);
    if (res.ok) router.push("/transactions");
    else setError(res.error);
  }

  async function onDelete() {
    if (!initial) return;
    if (!confirm("この取引を削除しますか？")) return;
    setSaving(true);
    const res = await deleteTransactionAction(initial.id);
    setSaving(false);
    if (res.ok) router.push("/transactions");
    else setError(res.error);
  }

  const mainLabel =
    mode === "INCOME" ? "売上科目" : mode === "TRANSFER" ? "振替先（入金）" : "費用科目";
  const counterLabel =
    mode === "INCOME" ? "入金先" : mode === "TRANSFER" ? "振替元（出金）" : "支払方法";
  const mainOptions = mode === "INCOME" ? revenueAccounts : mode === "EXPENSE" ? expenseAccounts : paymentAccounts;

  return (
    <div className="space-y-5">
      {/* mode tabs */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
        {MODES.map((m) => (
          <button
            key={m.key}
            type="button"
            onClick={() => setMode(m.key)}
            className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              mode === m.key ? "bg-white text-brand-700 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="card p-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="label">日付</label>
            <input type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div>
            <label className="label">取引先（任意）</label>
            <select className="input" value={partnerId} onChange={(e) => setPartnerId(e.target.value)}>
              <option value="">—</option>
              {partners.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="label">摘要</label>
            <input
              className="input"
              placeholder="例: クラウド利用料 / ◯月分 業務委託料"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <ReceiptScanner onResult={onScan} />
            {attachments.length > 0 && (
              <p className="mt-2 text-xs text-emerald-600">
                領収書 {attachments.length} 件を添付（保存時に登録されます）
              </p>
            )}
          </div>
        </div>
      </div>

      {mode !== "JOURNAL" ? (
        <div className="card p-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="label">{mainLabel}</label>
              <select className="input" value={mainAccountId} onChange={(e) => setMainAccountId(e.target.value)}>
                {mainOptions.map((a) => (
                  <option key={a.id} value={a.id}>{a.code} {a.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">{counterLabel}</label>
              <select className="input" value={counterAccountId} onChange={(e) => setCounterAccountId(e.target.value)}>
                {paymentAccounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.code} {a.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">金額（税込）</label>
              <input
                type="number"
                className="input text-right tabular-nums"
                value={amount || ""}
                onChange={(e) => setAmount(Number(e.target.value))}
              />
            </div>
            {mode !== "TRANSFER" && (
              <div>
                <label className="label">消費税区分</label>
                <select className="input" value={taxCategory} onChange={(e) => setTaxCategory(e.target.value as TaxCategory)}>
                  {Object.entries(TAX_CATEGORIES).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-slate-400">うち消費税 {formatYen(innerTax)}</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <JournalEditor accounts={accounts} lines={lines} setLines={setLines} debitSum={debitSum} creditSum={creditSum} balanced={balanced} />
      )}

      <div className="card p-5">
        <label className="label">メモ（任意）</label>
        <input className="input" value={note} onChange={(e) => setNote(e.target.value)} />
      </div>

      {error && <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</div>}

      <div className="flex items-center justify-between">
        <div>
          {initial && (
            <button type="button" className="btn-danger" onClick={onDelete} disabled={saving}>
              <Trash2 size={16} /> 削除
            </button>
          )}
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn-secondary" onClick={() => router.back()} disabled={saving}>
            キャンセル
          </button>
          <button type="button" className="btn-primary" onClick={onSubmit} disabled={saving}>
            {saving ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}

function JournalEditor({
  accounts,
  lines,
  setLines,
  debitSum,
  creditSum,
  balanced,
}: {
  accounts: Account[];
  lines: LineState[];
  setLines: (l: LineState[]) => void;
  debitSum: number;
  creditSum: number;
  balanced: boolean;
}) {
  const update = (key: string, patch: Partial<LineState>) =>
    setLines(lines.map((l) => (l.key === key ? { ...l, ...patch } : l)));
  const add = (side: "DEBIT" | "CREDIT") =>
    setLines([
      ...lines,
      { key: newKey(), accountId: accounts[0]?.id ?? "", side, amount: 0, taxCategory: side === "DEBIT" ? "TAXABLE_10" : "OUT_OF_SCOPE" },
    ]);
  const remove = (key: string) => setLines(lines.filter((l) => l.key !== key));

  return (
    <div className="card p-5">
      <div className="mb-2 grid grid-cols-12 gap-2 text-xs font-medium text-slate-400">
        <div className="col-span-2">貸借</div>
        <div className="col-span-4">勘定科目</div>
        <div className="col-span-3">税区分</div>
        <div className="col-span-2 text-right">金額</div>
        <div className="col-span-1" />
      </div>
      <div className="space-y-2">
        {lines.map((l) => (
          <div key={l.key} className="grid grid-cols-12 items-center gap-2">
            <select className="input col-span-2 px-2" value={l.side} onChange={(e) => update(l.key, { side: e.target.value as "DEBIT" | "CREDIT" })}>
              <option value="DEBIT">借方</option>
              <option value="CREDIT">貸方</option>
            </select>
            <select className="input col-span-4" value={l.accountId} onChange={(e) => update(l.key, { accountId: e.target.value })}>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.code} {a.name}</option>
              ))}
            </select>
            <select className="input col-span-3 px-2" value={l.taxCategory} onChange={(e) => update(l.key, { taxCategory: e.target.value as TaxCategory })}>
              {Object.entries(TAX_CATEGORIES).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            <input
              type="number"
              className="input col-span-2 text-right tabular-nums"
              value={l.amount || ""}
              onChange={(e) => update(l.key, { amount: Number(e.target.value) })}
            />
            <button type="button" className="col-span-1 flex justify-center text-slate-400 hover:text-red-500" onClick={() => remove(l.key)}>
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <button type="button" className="btn-secondary text-xs" onClick={() => add("DEBIT")}>
          <Plus size={14} /> 借方行
        </button>
        <button type="button" className="btn-secondary text-xs" onClick={() => add("CREDIT")}>
          <Plus size={14} /> 貸方行
        </button>
      </div>
      <div className={`mt-3 flex justify-end gap-6 rounded-lg px-4 py-2 text-sm ${balanced ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
        <span>借方 {formatYen(debitSum)}</span>
        <span>貸方 {formatYen(creditSum)}</span>
        <span className="font-semibold">{balanced ? "一致 ✓" : `差額 ${formatYen(debitSum - creditSum)}`}</span>
      </div>
    </div>
  );
}
