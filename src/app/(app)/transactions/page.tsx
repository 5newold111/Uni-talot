import Link from "next/link";
import { Plus, Download, Pencil } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/ui";
import {
  listAccounts,
  listPartners,
  listTransactions,
  type TxFilter,
} from "@/lib/repo";
import { formatYen, formatDate } from "@/lib/format";
import { TX_KINDS, labelOf, type TxKind } from "@/lib/constants";

export const dynamic = "force-dynamic";

const KIND_TONE: Record<string, string> = {
  INCOME: "bg-brand-50 text-brand-700",
  EXPENSE: "bg-amber-50 text-amber-700",
  TRANSFER: "bg-slate-100 text-slate-600",
  JOURNAL: "bg-violet-50 text-violet-700",
};

export default async function TransactionsPage({
  searchParams,
}: {
  searchParams: { kind?: string; from?: string; to?: string };
}) {
  const filter: TxFilter = {
    kind: (searchParams.kind as TxKind) || undefined,
    from: searchParams.from || undefined,
    to: searchParams.to || undefined,
  };
  const [txs, accounts, partners] = await Promise.all([
    listTransactions(filter),
    listAccounts(),
    listPartners(),
  ]);
  const accName = new Map(accounts.map((a) => [a.id, `${a.name}`]));
  const ptnName = new Map(partners.map((p) => [p.id, p.name]));

  const total = txs.reduce(
    (s, t) => s + t.lines.filter((l) => l.side === "DEBIT").reduce((x, l) => x + l.amount, 0),
    0,
  );

  return (
    <div>
      <PageHeader
        title="取引・仕訳"
        description={`${txs.length} 件 ・ 合計 ${formatYen(total)}`}
        action={
          <div className="flex gap-2">
            <Link href="/api/export/journal" className="btn-secondary">
              <Download size={16} /> CSV
            </Link>
            <Link href="/transactions/new" className="btn-primary">
              <Plus size={16} /> 取引を入力
            </Link>
          </div>
        }
      />

      {/* filter */}
      <form className="mb-4 flex flex-wrap items-end gap-3 card p-4">
        <div>
          <label className="label">種別</label>
          <select name="kind" defaultValue={searchParams.kind ?? ""} className="input w-36">
            <option value="">すべて</option>
            {Object.entries(TX_KINDS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">期間（開始）</label>
          <input type="date" name="from" defaultValue={searchParams.from ?? ""} className="input w-40" />
        </div>
        <div>
          <label className="label">期間（終了）</label>
          <input type="date" name="to" defaultValue={searchParams.to ?? ""} className="input w-40" />
        </div>
        <button className="btn-secondary" type="submit">絞り込み</button>
        <Link href="/transactions" className="text-xs text-slate-400 hover:underline">クリア</Link>
      </form>

      {txs.length === 0 ? (
        <EmptyState message="該当する取引がありません" />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="border-b border-slate-100 bg-slate-50/60">
              <tr>
                <th className="th">日付</th>
                <th className="th">種別</th>
                <th className="th">摘要 / 取引先</th>
                <th className="th">借方</th>
                <th className="th">貸方</th>
                <th className="th text-right">金額</th>
                <th className="th text-right">うち税</th>
                <th className="th" />
              </tr>
            </thead>
            <tbody>
              {txs.map((t) => {
                const debit = t.lines.filter((l) => l.side === "DEBIT");
                const credit = t.lines.filter((l) => l.side === "CREDIT");
                const amount = debit.reduce((s, l) => s + l.amount, 0);
                const tax = t.lines.reduce((s, l) => s + l.taxAmount, 0);
                return (
                  <tr key={t.id} className="border-b border-slate-50 hover:bg-slate-50/50 last:border-0">
                    <td className="td whitespace-nowrap text-slate-500">{formatDate(t.date)}</td>
                    <td className="td">
                      <span className={`badge ${KIND_TONE[t.kind] ?? "bg-slate-100"}`}>
                        {labelOf(TX_KINDS, t.kind)}
                      </span>
                    </td>
                    <td className="td">
                      <div className="font-medium">{t.description}</div>
                      {t.partnerId && (
                        <div className="text-xs text-slate-400">{ptnName.get(t.partnerId)}</div>
                      )}
                    </td>
                    <td className="td text-xs text-slate-500">
                      {debit.map((l) => accName.get(l.accountId)).join(" / ")}
                    </td>
                    <td className="td text-xs text-slate-500">
                      {credit.map((l) => accName.get(l.accountId)).join(" / ")}
                    </td>
                    <td className="td text-right tabular-nums font-medium">{formatYen(amount)}</td>
                    <td className="td text-right tabular-nums text-slate-400">{tax ? formatYen(tax) : "—"}</td>
                    <td className="td text-right">
                      <Link href={`/transactions/${t.id}/edit`} className="text-slate-400 hover:text-brand-600">
                        <Pencil size={15} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
