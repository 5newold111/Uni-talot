"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Copy, Ban, Check } from "lucide-react";
import { createShareLinkAction, revokeShareLinkAction } from "@/app/actions";
import { SHARE_SCOPES, type ShareScope } from "@/lib/constants";
import { formatDate } from "@/lib/format";
import type { ShareLink } from "@/lib/types";

export function ShareManager({
  links,
  baseUrl,
}: {
  links: ShareLink[];
  baseUrl: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState("");
  const [scope, setScope] = useState<ShareScope>("READONLY");
  const [year, setYear] = useState<number>(new Date().getFullYear());
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  async function create() {
    setBusy(true);
    const res = await createShareLinkAction({
      label,
      scope,
      fiscalYear: year,
      expiresAt: null,
    });
    setBusy(false);
    if (res.ok) {
      setOpen(false);
      setLabel("");
      router.refresh();
    } else alert(res.error);
  }

  async function copy(token: string) {
    const url = `${baseUrl}/shared/${token}`;
    await navigator.clipboard.writeText(url);
    setCopied(token);
    setTimeout(() => setCopied(null), 1500);
  }

  const active = links.filter((l) => !l.revokedAt);
  const revoked = links.filter((l) => l.revokedAt);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button className="btn-primary" onClick={() => setOpen(!open)}>
          <Plus size={16} /> 共有リンクを発行
        </button>
      </div>

      {open && (
        <div className="card p-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="label">ラベル（任意）</label>
              <input className="input" placeholder="◯◯税理士事務所" value={label} onChange={(e) => setLabel(e.target.value)} />
            </div>
            <div>
              <label className="label">権限</label>
              <select className="input" value={scope} onChange={(e) => setScope(e.target.value as ShareScope)}>
                {Object.entries(SHARE_SCOPES).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">対象年度</label>
              <input type="number" className="input" value={year} onChange={(e) => setYear(Number(e.target.value))} />
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button className="btn-secondary" onClick={() => setOpen(false)}>キャンセル</button>
            <button className="btn-primary" onClick={create} disabled={busy}>{busy ? "発行中…" : "発行"}</button>
          </div>
        </div>
      )}

      {active.length === 0 ? (
        <div className="card px-6 py-12 text-center text-sm text-slate-400">
          有効な共有リンクはありません
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="border-b border-slate-100 bg-slate-50/60">
              <tr>
                <th className="th">ラベル</th>
                <th className="th">権限</th>
                <th className="th">年度</th>
                <th className="th">発行日</th>
                <th className="th" />
              </tr>
            </thead>
            <tbody>
              {active.map((l) => (
                <tr key={l.id} className="border-b border-slate-50 last:border-0">
                  <td className="td font-medium">{l.label || "（無題）"}</td>
                  <td className="td text-xs">{SHARE_SCOPES[l.scope]}</td>
                  <td className="td text-xs text-slate-500">{l.fiscalYear ?? "—"}</td>
                  <td className="td text-xs text-slate-400">{formatDate(l.createdAt)}</td>
                  <td className="td">
                    <div className="flex justify-end gap-2">
                      <button className="btn-secondary text-xs" onClick={() => copy(l.token)}>
                        {copied === l.token ? <Check size={14} /> : <Copy size={14} />}
                        {copied === l.token ? "コピー済" : "URLをコピー"}
                      </button>
                      <button
                        className="btn-danger text-xs"
                        onClick={async () => {
                          if (!confirm("このリンクを無効化しますか？")) return;
                          const res = await revokeShareLinkAction(l.id);
                          if (res.ok) router.refresh();
                          else alert(res.error);
                        }}
                      >
                        <Ban size={14} /> 無効化
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {revoked.length > 0 && (
        <p className="text-xs text-slate-400">無効化済み: {revoked.length} 件</p>
      )}
    </div>
  );
}
