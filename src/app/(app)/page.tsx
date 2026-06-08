import Link from "next/link";
import { Plus } from "lucide-react";
import { PageHeader, StatCard } from "@/components/ui";
import { MonthlyChart, CategoryBars } from "@/components/MonthlyChart";
import { listAccounts, listTransactions, getCurrentUser } from "@/lib/repo";
import {
  dashboardSummary,
  monthlySeries,
  profitAndLoss,
} from "@/lib/reports";
import { formatYen, formatDate } from "@/lib/format";
import { TX_KINDS, labelOf } from "@/lib/constants";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [accounts, txs, user] = await Promise.all([
    listAccounts(),
    listTransactions(),
    getCurrentUser(),
  ]);
  const year = new Date().getFullYear();
  const summary = dashboardSummary(accounts, txs);
  const monthly = monthlySeries(accounts, txs, year);
  const pl = profitAndLoss(accounts, txs);

  const topExpenses = pl.expense
    .slice()
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 6)
    .map((e) => ({ name: e.account.name, value: e.amount }));

  const recent = txs.slice(0, 6);

  return (
    <div>
      <PageHeader
        title={`ダッシュボード`}
        description={`${user.businessName || user.name} ・ ${year}年`}
        action={
          <Link href="/transactions/new" className="btn-primary">
            <Plus size={16} /> 取引を入力
          </Link>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="売上（年初来）" value={formatYen(summary.totalRevenue)} tone="brand" />
        <StatCard label="経費（年初来）" value={formatYen(summary.totalExpense)} />
        <StatCard
          label="所得（利益）"
          value={formatYen(summary.netIncome)}
          tone={summary.netIncome >= 0 ? "positive" : "negative"}
        />
        <StatCard
          label="現預金 / 売掛"
          value={formatYen(summary.cash)}
          sub={`売掛金 ${formatYen(summary.receivable)}`}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            月次の売上・経費・利益（{year}年）
          </h2>
          <MonthlyChart data={monthly} />
        </div>
        <div className="card p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">経費の内訳（上位）</h2>
          {topExpenses.length > 0 ? (
            <CategoryBars data={topExpenses} />
          ) : (
            <p className="py-10 text-center text-sm text-slate-400">データがありません</p>
          )}
        </div>
      </div>

      <div className="mt-6 card p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">最近の取引</h2>
          <Link href="/transactions" className="text-xs font-medium text-brand-600 hover:underline">
            すべて見る →
          </Link>
        </div>
        {recent.length > 0 ? (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="th">日付</th>
                <th className="th">摘要</th>
                <th className="th">種別</th>
                <th className="th text-right">金額</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((t) => {
                const amount = t.lines
                  .filter((l) => l.side === "DEBIT")
                  .reduce((s, l) => s + l.amount, 0);
                return (
                  <tr key={t.id} className="border-b border-slate-50 last:border-0">
                    <td className="td whitespace-nowrap text-slate-500">{formatDate(t.date)}</td>
                    <td className="td font-medium">{t.description}</td>
                    <td className="td">
                      <span className="badge bg-slate-100 text-slate-600">
                        {labelOf(TX_KINDS, t.kind)}
                      </span>
                    </td>
                    <td className="td text-right tabular-nums">{formatYen(amount)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <p className="py-8 text-center text-sm text-slate-400">
            まだ取引がありません。「取引を入力」から記帳を始めましょう。
          </p>
        )}
      </div>
    </div>
  );
}
