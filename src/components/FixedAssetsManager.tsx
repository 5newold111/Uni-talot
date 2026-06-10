"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Pencil, Trash2, CalendarClock } from "lucide-react";
import { saveFixedAssetAction, deleteFixedAssetAction } from "@/app/actions";
import {
  DEPRECIATION_METHODS,
  type DepreciationMethod,
} from "@/lib/constants";
import { depreciationForYear, depreciationSchedule } from "@/lib/depreciation";
import { formatYen, todayIso } from "@/lib/format";
import type { Account, FixedAsset } from "@/lib/types";

export function FixedAssetsManager({
  assets,
  accounts,
  year,
}: {
  assets: FixedAsset[];
  accounts: Account[];
  year: number;
}) {
  const router = useRouter();
  const [editing, setEditing] = useState<FixedAsset | "new" | null>(null);
  const [detail, setDetail] = useState<FixedAsset | null>(null);

  const assetAccounts = accounts.filter((a) => a.type === "ASSET");
  const totalThisYear = assets.reduce(
    (s, a) => s + depreciationForYear(a, year).expense,
    0,
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-500">
          {year}年の減価償却費（必要経費算入額）合計：{" "}
          <span className="font-semibold text-slate-700">{formatYen(totalThisYear)}</span>
        </div>
        <button className="btn-primary" onClick={() => setEditing("new")}>
          <Plus size={16} /> 資産を登録
        </button>
      </div>

      {assets.length === 0 ? (
        <div className="card px-6 py-16 text-center text-sm text-slate-400">
          固定資産が登録されていません
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="border-b border-slate-100 bg-slate-50/60">
              <tr>
                <th className="th">資産名</th>
                <th className="th">取得日</th>
                <th className="th">方法</th>
                <th className="th text-right">取得価額</th>
                <th className="th text-right">本年償却費</th>
                <th className="th text-right">期末簿価</th>
                <th className="th" />
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => {
                const d = depreciationForYear(a, year);
                return (
                  <tr key={a.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/50">
                    <td className="td font-medium">{a.name}</td>
                    <td className="td whitespace-nowrap text-slate-500">{a.acquisitionDate}</td>
                    <td className="td text-xs text-slate-500">{DEPRECIATION_METHODS[a.method]}</td>
                    <td className="td text-right tabular-nums">{formatYen(a.acquisitionCost)}</td>
                    <td className="td text-right tabular-nums font-medium">{formatYen(d.expense)}</td>
                    <td className="td text-right tabular-nums text-slate-500">{formatYen(d.bookValue)}</td>
                    <td className="td">
                      <div className="flex justify-end gap-2">
                        <button onClick={() => setDetail(a)} className="text-slate-400 hover:text-brand-600" title="償却スケジュール">
                          <CalendarClock size={15} />
                        </button>
                        <button onClick={() => setEditing(a)} className="text-slate-400 hover:text-brand-600">
                          <Pencil size={15} />
                        </button>
                        <DeleteButton id={a.id} onDone={() => router.refresh()} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <AssetModal
          asset={editing === "new" ? null : editing}
          assetAccounts={assetAccounts}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            router.refresh();
          }}
        />
      )}
      {detail && <ScheduleModal asset={detail} onClose={() => setDetail(null)} />}
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
        if (!confirm("この資産を削除しますか？")) return;
        setBusy(true);
        const res = await deleteFixedAssetAction(id);
        setBusy(false);
        if (!res.ok) alert(res.error);
        else onDone();
      }}
    >
      <Trash2 size={15} />
    </button>
  );
}

function AssetModal({
  asset,
  assetAccounts,
  onClose,
  onSaved,
}: {
  asset: FixedAsset | null;
  assetAccounts: Account[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(asset?.name ?? "");
  const [acquisitionDate, setAcquisitionDate] = useState(asset?.acquisitionDate ?? todayIso());
  const [startDate, setStartDate] = useState(asset?.startDate ?? asset?.acquisitionDate ?? todayIso());
  const [acquisitionCost, setAcquisitionCost] = useState<number>(asset?.acquisitionCost ?? 0);
  const [method, setMethod] = useState<DepreciationMethod>(asset?.method ?? "STRAIGHT_LINE");
  const [usefulLife, setUsefulLife] = useState<number>(asset?.usefulLife ?? 5);
  const [businessRatio, setBusinessRatio] = useState<number>(asset?.businessRatio ?? 100);
  const [accountId, setAccountId] = useState(asset?.accountId ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!name.trim()) return setError("資産名は必須です");
    if (acquisitionCost <= 0) return setError("取得価額を入力してください");
    setBusy(true);
    const res = await saveFixedAssetAction(
      {
        name: name.trim(),
        acquisitionDate,
        startDate: startDate || acquisitionDate,
        acquisitionCost: Math.round(acquisitionCost),
        usefulLife: method === "STRAIGHT_LINE" ? usefulLife : 0,
        method,
        businessRatio: businessRatio || 100,
        accountId: accountId || null,
        note: "",
      },
      asset?.id,
    );
    setBusy(false);
    if (res.ok) onSaved();
    else setError(res.error);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <div className="card w-full max-w-lg p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-4 text-base font-bold">{asset ? "資産を編集" : "資産を登録"}</h3>
        <div className="space-y-3">
          <div>
            <label className="label">資産名</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="例: ノートPC" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">取得年月日</label>
              <input type="date" className="input" value={acquisitionDate} onChange={(e) => setAcquisitionDate(e.target.value)} />
            </div>
            <div>
              <label className="label">事業供用開始日</label>
              <input type="date" className="input" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">取得価額（円）</label>
              <input type="number" className="input text-right" value={acquisitionCost || ""} onChange={(e) => setAcquisitionCost(Number(e.target.value))} />
            </div>
            <div>
              <label className="label">事業専用割合（%）</label>
              <input type="number" className="input text-right" value={businessRatio} onChange={(e) => setBusinessRatio(Number(e.target.value))} />
            </div>
          </div>
          <div>
            <label className="label">償却方法</label>
            <select className="input" value={method} onChange={(e) => setMethod(e.target.value as DepreciationMethod)}>
              {Object.entries(DEPRECIATION_METHODS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          {method === "STRAIGHT_LINE" && (
            <div>
              <label className="label">耐用年数（年）</label>
              <input type="number" className="input" value={usefulLife} onChange={(e) => setUsefulLife(Number(e.target.value))} />
            </div>
          )}
          {method === "IMMEDIATE" && (
            <p className="text-xs text-slate-400">少額減価償却資産の特例：取得価額30万円未満が対象（年間合計300万円まで）。</p>
          )}
          {method === "LUMP_3YEAR" && (
            <p className="text-xs text-slate-400">一括償却資産：取得価額20万円未満が対象。3年で均等償却します。</p>
          )}
          <div>
            <label className="label">対応する資産科目（任意）</label>
            <select className="input" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
              <option value="">—</option>
              {assetAccounts.map((a) => (
                <option key={a.id} value={a.id}>{a.code} {a.name}</option>
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

function ScheduleModal({ asset, onClose }: { asset: FixedAsset; onClose: () => void }) {
  const schedule = depreciationSchedule(asset);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <div className="card w-full max-w-lg p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-1 text-base font-bold">{asset.name} の償却スケジュール</h3>
        <p className="mb-3 text-xs text-slate-400">
          {DEPRECIATION_METHODS[asset.method]} ・ 取得価額 {formatYen(asset.acquisitionCost)}
        </p>
        <div className="max-h-80 overflow-y-auto">
          <table className="w-full">
            <thead className="sticky top-0 bg-white">
              <tr className="border-b border-slate-100">
                <th className="th">年</th>
                <th className="th text-right">月数</th>
                <th className="th text-right">償却額</th>
                <th className="th text-right">経費算入</th>
                <th className="th text-right">期末簿価</th>
              </tr>
            </thead>
            <tbody>
              {schedule.map((r) => (
                <tr key={r.year} className="border-b border-slate-50 last:border-0">
                  <td className="td">{r.year}年</td>
                  <td className="td text-right text-slate-500">{r.months}</td>
                  <td className="td text-right tabular-nums">{formatYen(r.depreciation)}</td>
                  <td className="td text-right tabular-nums">{formatYen(r.expense)}</td>
                  <td className="td text-right tabular-nums text-slate-500">{formatYen(r.bookValue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex justify-end">
          <button className="btn-secondary" onClick={onClose}>閉じる</button>
        </div>
      </div>
    </div>
  );
}
