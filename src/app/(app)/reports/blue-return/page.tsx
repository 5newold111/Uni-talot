import Link from "next/link";
import { Download, AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/ui";
import { PrintButton } from "@/components/PrintButton";
import {
  getCurrentUser,
  listAccounts,
  listFixedAssets,
  listTransactions,
} from "@/lib/repo";
import { balanceSheet } from "@/lib/reports";
import { blueReturnStatement } from "@/lib/taxReturn";
import { depreciationForYear } from "@/lib/depreciation";
import { formatYen } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function BlueReturnPage({
  searchParams,
}: {
  searchParams: { year?: string };
}) {
  const user = await getCurrentUser();
  const year = Number(searchParams.year) || new Date().getFullYear();
  const [accounts, txs, assets] = await Promise.all([
    listAccounts(),
    listTransactions({ from: `${year}-01-01`, to: `${year}-12-31` }),
    listFixedAssets(),
  ]);

  const computedDepreciation = assets.reduce(
    (s, a) => s + depreciationForYear(a, year).expense,
    0,
  );
  const stmt = blueReturnStatement(accounts, txs, {
    blueDeduction: user.blueDeduction ?? 0,
    computedDepreciation,
  });
  const bs = balanceSheet(accounts, txs);

  // 記帳済みの減価償却費（科目521）と固定資産から計算した額の差
  const recordedDep =
    stmt.expenses.find((e) => e.account.code === "521")?.amount ?? 0;
  const depGap = computedDepreciation - recordedDep;

  const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);
  const Row = ({ label, value, bold }: { label: string; value: number; bold?: boolean }) => (
    <div className={`flex justify-between border-b border-slate-50 py-1.5 ${bold ? "font-semibold" : ""}`}>
      <span>{label}</span>
      <span className="tabular-nums">{formatYen(value)}</span>
    </div>
  );

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="青色申告決算書（一般用）"
        description={`${user.businessName || user.name} ・ ${year}年分`}
        action={
          <div className="flex items-center gap-2 print:hidden">
            <form>
              <input type="hidden" name="year" />
            </form>
            <PrintButton />
            <Link href={`/api/export/blue-return?year=${year}`} className="btn-secondary">
              <Download size={16} /> CSV
            </Link>
          </div>
        }
      />

      <form className="mb-4 flex gap-2 print:hidden">
        <select name="year" defaultValue={String(year)} className="input w-32">
          {years.map((y) => (
            <option key={y} value={y}>{y}年分</option>
          ))}
        </select>
        <button className="btn-secondary" type="submit">表示</button>
      </form>

      {depGap !== 0 && (
        <div className="mb-4 flex items-start gap-2 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800 print:hidden">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <div>
            固定資産から計算した本年の減価償却費は <strong>{formatYen(computedDepreciation)}</strong> ですが、
            帳簿の「減価償却費」は <strong>{formatYen(recordedDep)}</strong> です。
            差額 {formatYen(depGap)} を仕訳（借方 減価償却費 / 貸方 工具器具備品）で計上すると一致します。
          </div>
        </div>
      )}

      {/* 損益計算書部 */}
      <section className="card mb-6 p-6">
        <h2 className="mb-4 border-b border-slate-200 pb-2 text-base font-bold">損益計算書</h2>

        <div className="mb-4">
          <div className="mb-1 text-xs font-semibold text-slate-500">収入金額</div>
          <Row label="売上（収入）金額" value={stmt.income.sales} />
          <Row label="雑収入" value={stmt.income.misc} />
          <Row label="計" value={stmt.income.total} bold />
        </div>

        <div className="mb-4">
          <div className="mb-1 text-xs font-semibold text-slate-500">売上原価</div>
          <Row label="期首商品（製品）棚卸高" value={stmt.cost.opening} />
          <Row label="仕入金額" value={stmt.cost.purchase} />
          <Row label="期末商品（製品）棚卸高" value={stmt.cost.closing} />
          <Row label="差引原価" value={stmt.cost.total} bold />
        </div>

        <div className="mb-4 flex justify-between rounded-lg bg-slate-50 px-4 py-2 font-semibold">
          <span>差引金額（売上総利益）</span>
          <span className="tabular-nums">{formatYen(stmt.grossProfit)}</span>
        </div>

        <div className="mb-4">
          <div className="mb-1 text-xs font-semibold text-slate-500">経費</div>
          {stmt.expenses.map((e) => (
            <Row key={e.account.id} label={e.account.name} value={e.amount} />
          ))}
          <Row label="経費計" value={stmt.expenseTotal} bold />
        </div>

        <div className="space-y-2">
          <div className="flex justify-between rounded-lg bg-slate-50 px-4 py-2 font-semibold">
            <span>青色申告特別控除前の所得金額</span>
            <span className="tabular-nums">{formatYen(stmt.preDeductionIncome)}</span>
          </div>
          <div className="flex justify-between px-4 py-1 text-slate-600">
            <span>青色申告特別控除額</span>
            <span className="tabular-nums">- {formatYen(stmt.blueDeduction)}</span>
          </div>
          <div className="flex justify-between rounded-lg bg-emerald-50 px-4 py-3 text-lg font-bold text-emerald-700">
            <span>所得金額</span>
            <span className="tabular-nums">{formatYen(stmt.incomeAmount)}</span>
          </div>
        </div>
      </section>

      {/* 貸借対照表部 */}
      <section className="card mb-6 p-6">
        <h2 className="mb-4 border-b border-slate-200 pb-2 text-base font-bold">貸借対照表（{year}年12月31日）</h2>
        <div className="grid grid-cols-2 gap-6">
          <div>
            <div className="mb-1 text-xs font-semibold text-slate-500">資産の部</div>
            {bs.assets.map((r) => <Row key={r.account.id} label={r.account.name} value={r.amount} />)}
            <Row label="資産合計" value={bs.totalAssets} bold />
          </div>
          <div>
            <div className="mb-1 text-xs font-semibold text-slate-500">負債・資本の部</div>
            {bs.liabilities.map((r) => <Row key={r.account.id} label={r.account.name} value={r.amount} />)}
            {bs.equity.map((r) => <Row key={r.account.id} label={r.account.name} value={r.amount} />)}
            <Row label="当期純利益（元入金繰入前）" value={bs.netIncome} />
            <Row label="負債・資本合計" value={bs.totalLiabilities + bs.totalEquity} bold />
          </div>
        </div>
      </section>

      <p className="text-xs text-slate-400">
        ※ 本表は記帳データから自動集計した参考様式です。提出様式（国税庁フォーマット）への転記・最終確認は
        税理士または会計ソフトで行ってください。棚卸・専従者給与・各種引当金等は本MVPでは未対応です。
      </p>
    </div>
  );
}
