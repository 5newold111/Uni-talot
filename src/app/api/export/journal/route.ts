// 仕訳帳CSVエクスポート（税理士共有・会計ソフト取込用）。
import { listAccounts, listPartners, listTransactions } from "@/lib/repo";
import { TAX_CATEGORIES, SIDES, labelOf } from "@/lib/constants";
import { toCsv, csvResponse } from "@/lib/csv";

export const dynamic = "force-dynamic";

export async function GET() {
  const [txs, accounts, partners] = await Promise.all([
    listTransactions(),
    listAccounts(),
    listPartners(),
  ]);
  const accName = new Map(accounts.map((a) => [a.id, `${a.code} ${a.name}`]));
  const ptnName = new Map(partners.map((p) => [p.id, p.name]));

  const headers = [
    "伝票番号",
    "日付",
    "種別",
    "摘要",
    "取引先",
    "貸借",
    "勘定科目",
    "金額",
    "消費税区分",
    "税率",
    "消費税額",
  ];
  const rows: (string | number)[][] = [];
  // 日付昇順で
  const sorted = txs.slice().sort((a, b) => a.date.localeCompare(b.date) || (a.slipNumber ?? 0) - (b.slipNumber ?? 0));
  for (const t of sorted) {
    for (const l of t.lines) {
      rows.push([
        t.slipNumber ?? "",
        t.date,
        labelOf({ EXPENSE: "経費", INCOME: "売上", TRANSFER: "振替", JOURNAL: "仕訳" }, t.kind),
        t.description,
        t.partnerId ? ptnName.get(t.partnerId) ?? "" : "",
        labelOf(SIDES, l.side),
        accName.get(l.accountId) ?? "",
        l.amount,
        labelOf(TAX_CATEGORIES, l.taxCategory),
        l.taxRate ? `${l.taxRate}%` : "",
        l.taxAmount,
      ]);
    }
  }
  const csv = toCsv(headers, rows);
  const date = new Date().toISOString().slice(0, 10);
  return csvResponse(`仕訳帳_${date}.csv`, csv);
}
