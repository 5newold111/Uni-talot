import Link from "next/link";
import { Download } from "lucide-react";
import { PageHeader } from "@/components/ui";
import { listAccounts, listTransactions, getCurrentUser } from "@/lib/repo";
import {
  balanceSheet,
  consumptionTaxSummary,
  profitAndLoss,
} from "@/lib/reports";
import { formatYen } from "@/lib/format";
import { CONSUMPTION_TAX_STATUS, labelOf } from "@/lib/constants";

export const dynamic = "force-dynamic";

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: { year?: string };
}) {
  const user = await getCurrentUser();
  const year = Number(searchParams.year) || new Date().getFullYear();
  const from = `${year}-01-01`;
  const to = `${year}-12-31`;
  const [accounts, txs] = await Promise.all([
    listAccounts(),
    listTransactions({ from, to }),
  ]);

  const pl = profitAndLoss(accounts, txs);
  const bs = balanceSheet(accounts, txs);
  const tax = consumptionTaxSummary(accounts, txs);

  const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);

  return (
    <div>
      <PageHeader
        title="レポート"
        description={`${year}年 ・ ${labelOf(CONSUMPTION_TAX_STATUS, user.consumptionTaxStatus)}`}
        action={
          <Link href="/api/export/journal" className="btn-secondary">
            <Download size={16} /> 仕訳CSV
          </Link>
        }
      />
      <form className="mb-4 flex gap-2">
        <select name="year" defaultValue={String(year)} className="input w-32">
          {years.map((y) => (
            <option key={y} value={y}>{y}年</option>
          ))}
        </select>
        <button className="btn-secondary" type="submit">表示</button>
      </form>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* P/L */}
        <section className="card p-5">
          <h2 className="mb-3 text-sm font-bold text-slate-700">損益計算書（P/L）</h2>
          <ReportTable
            groups={[
              { title: "売上・収益", rows: pl.revenue.map((r) => ({ label: `${r.account.name}`, value: r.amount })), total: pl.totalRevenue },
              { title: "経費・費用", rows: pl.expense.map((r) => ({ label: `${r.account.name}`, value: r.amount })), total: pl.totalExpense },
            ]}
          />
          <div className="mt-3 flex items-center justify-between rounded-lg bg-emerald-50 px-4 py-3">
            <span className="text-sm font-semibold text-emerald-800">所得（当期純利益）</span>
            <span className="text-lg font-bold text-emerald-700 tabular-nums">{formatYen(pl.netIncome)}</span>
          </div>
        </section>

        {/* B/S */}
        <section className="card p-5">
          <h2 className="mb-3 text-sm font-bold text-slate-700">貸借対照表（B/S）</h2>
          <ReportTable
            groups={[
              { title: "資産", rows: bs.assets.map((r) => ({ label: r.account.name, value: r.amount })), total: bs.totalAssets },
              { title: "負債", rows: bs.liabilities.map((r) => ({ label: r.account.name, value: r.amount })), total: bs.totalLiabilities },
              {
                title: "純資産",
                rows: [
                  ...bs.equity.map((r) => ({ label: r.account.name, value: r.amount })),
                  { label: "当期純利益", value: bs.netIncome },
                ],
                total: bs.totalEquity,
              },
            ]}
          />
          <div className="mt-3 flex items-center justify-between rounded-lg bg-slate-50 px-4 py-2 text-xs text-slate-500">
            <span>資産合計 {formatYen(bs.totalAssets)}</span>
            <span>負債+純資産 {formatYen(bs.totalLiabilities + bs.totalEquity)}</span>
          </div>
        </section>
      </div>

      {/* 消費税 */}
      <section className="card mt-6 p-5">
        <h2 className="mb-3 text-sm font-bold text-slate-700">消費税集計（本則課税ベースの概算）</h2>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div>
            <div className="mb-1 text-xs font-semibold text-slate-500">売上にかかる消費税</div>
            <TaxTable rows={tax.sales} />
            <div className="mt-2 flex justify-between text-sm font-medium">
              <span>計</span><span className="tabular-nums">{formatYen(tax.salesTaxTotal)}</span>
            </div>
          </div>
          <div>
            <div className="mb-1 text-xs font-semibold text-slate-500">仕入・経費にかかる消費税（控除）</div>
            <TaxTable rows={tax.purchase} />
            <div className="mt-2 flex justify-between text-sm font-medium">
              <span>計</span><span className="tabular-nums">{formatYen(tax.purchaseTaxTotal)}</span>
            </div>
          </div>
        </div>
        <div className="mt-4 flex items-center justify-between rounded-lg bg-brand-50 px-4 py-3">
          <span className="text-sm font-semibold text-brand-800">納付見込（売上税額 − 仕入控除）</span>
          <span className="text-lg font-bold text-brand-700 tabular-nums">{formatYen(tax.estimatedPayable)}</span>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          ※ 概算です。実際の納税額は事業区分・控除要件・簡易課税のみなし仕入率等により異なります。確定申告時は税理士にご確認ください。
        </p>
      </section>
    </div>
  );
}

function ReportTable({
  groups,
}: {
  groups: { title: string; rows: { label: string; value: number }[]; total: number }[];
}) {
  return (
    <div className="space-y-4">
      {groups.map((g) => (
        <div key={g.title}>
          <div className="mb-1 text-xs font-semibold text-slate-500">{g.title}</div>
          <table className="w-full">
            <tbody>
              {g.rows.length === 0 ? (
                <tr><td className="td text-slate-300">—</td></tr>
              ) : (
                g.rows.map((r, i) => (
                  <tr key={i} className="border-b border-slate-50 last:border-0">
                    <td className="td">{r.label}</td>
                    <td className="td text-right tabular-nums">{formatYen(r.value)}</td>
                  </tr>
                ))
              )}
              <tr className="border-t border-slate-200">
                <td className="td font-semibold">小計</td>
                <td className="td text-right font-semibold tabular-nums">{formatYen(g.total)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function TaxTable({ rows }: { rows: { label: string; base: number; tax: number }[] }) {
  if (rows.length === 0) return <p className="py-3 text-sm text-slate-300">該当なし</p>;
  return (
    <table className="w-full">
      <thead>
        <tr className="border-b border-slate-100">
          <th className="th">区分</th>
          <th className="th text-right">本体</th>
          <th className="th text-right">消費税</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="border-b border-slate-50 last:border-0">
            <td className="td">{r.label}</td>
            <td className="td text-right tabular-nums text-slate-500">{formatYen(r.base)}</td>
            <td className="td text-right tabular-nums">{formatYen(r.tax)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
