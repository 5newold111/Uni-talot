// 青色申告決算書（損益計算書部）の CSV エクスポート。
import { getCurrentUser, listAccounts, listFixedAssets, listTransactions } from "@/lib/repo";
import { blueReturnStatement } from "@/lib/taxReturn";
import { depreciationForYear } from "@/lib/depreciation";
import { toCsv, csvResponse } from "@/lib/csv";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const year = Number(url.searchParams.get("year")) || new Date().getFullYear();
  const user = await getCurrentUser();
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

  const rows: (string | number)[][] = [
    ["区分", "項目", "金額"],
    ["収入金額", "売上（収入）金額", stmt.income.sales],
    ["収入金額", "雑収入", stmt.income.misc],
    ["収入金額", "計", stmt.income.total],
    ["売上原価", "期首棚卸高", stmt.cost.opening],
    ["売上原価", "仕入金額", stmt.cost.purchase],
    ["売上原価", "期末棚卸高", stmt.cost.closing],
    ["売上原価", "差引原価", stmt.cost.total],
    ["", "差引金額（売上総利益）", stmt.grossProfit],
    ...stmt.expenses.map((e) => ["経費", e.account.name, e.amount] as (string | number)[]),
    ["経費", "経費計", stmt.expenseTotal],
    ["", "青色申告特別控除前の所得金額", stmt.preDeductionIncome],
    ["", "青色申告特別控除額", stmt.blueDeduction],
    ["", "所得金額", stmt.incomeAmount],
  ];

  const csv = toCsv(rows[0] as string[], rows.slice(1));
  return csvResponse(`青色申告決算書_${year}.csv`, csv);
}
