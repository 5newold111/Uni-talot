import { notFound } from "next/navigation";
import { Receipt } from "lucide-react";
import {
  getShareLinkByToken,
  getUserById,
  listAccountsForUser,
  listTransactionsForUser,
} from "@/lib/repo";
import { profitAndLoss, dashboardSummary } from "@/lib/reports";
import { formatYen, formatDate } from "@/lib/format";
import { SHARE_SCOPES } from "@/lib/constants";

export const dynamic = "force-dynamic";

export default async function SharedViewPage({
  params,
}: {
  params: { token: string };
}) {
  const link = await getShareLinkByToken(params.token);
  if (!link) notFound();

  const year = link.fiscalYear ?? new Date().getFullYear();
  const [user, accounts, txs] = await Promise.all([
    getUserById(link.userId),
    listAccountsForUser(link.userId),
    listTransactionsForUser(link.userId, { from: `${year}-01-01`, to: `${year}-12-31` }),
  ]);
  if (!user) notFound();
  const pl = profitAndLoss(accounts, txs);
  const summary = dashboardSummary(accounts, txs);
  const accName = new Map(accounts.map((a) => [a.id, a.name]));

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white">
              <Receipt size={18} />
            </div>
            <div>
              <div className="text-sm font-bold">{user.businessName || user.name} の帳簿</div>
              <div className="text-xs text-slate-400">{year}年 ・ {SHARE_SCOPES[link.scope]}（共有ビュー）</div>
            </div>
          </div>
          <span className="badge bg-slate-100 text-slate-500">閲覧のみ</span>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 px-6 py-8">
        <div className="grid grid-cols-3 gap-4">
          <div className="card p-4">
            <div className="text-xs text-slate-500">売上</div>
            <div className="mt-1 text-xl font-bold text-brand-600">{formatYen(summary.totalRevenue)}</div>
          </div>
          <div className="card p-4">
            <div className="text-xs text-slate-500">経費</div>
            <div className="mt-1 text-xl font-bold">{formatYen(summary.totalExpense)}</div>
          </div>
          <div className="card p-4">
            <div className="text-xs text-slate-500">所得</div>
            <div className="mt-1 text-xl font-bold text-emerald-600">{formatYen(summary.netIncome)}</div>
          </div>
        </div>

        <section className="card p-5">
          <h2 className="mb-3 text-sm font-bold text-slate-700">損益計算書（{year}年）</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <div className="mb-1 text-xs font-semibold text-slate-500">収益</div>
              {pl.revenue.map((r) => (
                <div key={r.account.id} className="flex justify-between border-b border-slate-50 py-1.5 text-sm">
                  <span>{r.account.name}</span>
                  <span className="tabular-nums">{formatYen(r.amount)}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="mb-1 text-xs font-semibold text-slate-500">費用</div>
              {pl.expense.map((r) => (
                <div key={r.account.id} className="flex justify-between border-b border-slate-50 py-1.5 text-sm">
                  <span>{r.account.name}</span>
                  <span className="tabular-nums">{formatYen(r.amount)}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="card overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-3 text-sm font-bold text-slate-700">仕訳帳</div>
          <table className="w-full">
            <thead className="bg-slate-50/60">
              <tr>
                <th className="th">日付</th>
                <th className="th">摘要</th>
                <th className="th">借方</th>
                <th className="th">貸方</th>
                <th className="th text-right">金額</th>
              </tr>
            </thead>
            <tbody>
              {txs.map((t) => {
                const debit = t.lines.filter((l) => l.side === "DEBIT");
                const credit = t.lines.filter((l) => l.side === "CREDIT");
                const amount = debit.reduce((s, l) => s + l.amount, 0);
                return (
                  <tr key={t.id} className="border-b border-slate-50 last:border-0">
                    <td className="td whitespace-nowrap text-slate-500">{formatDate(t.date)}</td>
                    <td className="td">{t.description}</td>
                    <td className="td text-xs text-slate-500">{debit.map((l) => accName.get(l.accountId)).join(" / ")}</td>
                    <td className="td text-xs text-slate-500">{credit.map((l) => accName.get(l.accountId)).join(" / ")}</td>
                    <td className="td text-right tabular-nums">{formatYen(amount)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>

        <p className="text-center text-xs text-slate-400">会計フリー帳 ・ 共有ビュー</p>
      </main>
    </div>
  );
}
