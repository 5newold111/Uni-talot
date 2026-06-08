import Link from "next/link";
import { Plus, Pencil } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/ui";
import { listInvoices, listPartners } from "@/lib/repo";
import { formatYen, formatDate } from "@/lib/format";
import { INVOICE_STATUS } from "@/lib/constants";

export const dynamic = "force-dynamic";

const STATUS_TONE: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-600",
  SENT: "bg-brand-50 text-brand-700",
  PAID: "bg-emerald-50 text-emerald-700",
  VOID: "bg-red-50 text-red-600",
};

export default async function InvoicesPage() {
  const [invoices, partners] = await Promise.all([listInvoices(), listPartners()]);
  const ptnName = new Map(partners.map((p) => [p.id, p.name]));
  const totalUnpaid = invoices
    .filter((i) => i.status === "SENT")
    .reduce((s, i) => s + i.total, 0);

  return (
    <div>
      <PageHeader
        title="請求書"
        description={`${invoices.length} 件 ・ 未回収（送付済）${formatYen(totalUnpaid)}`}
        action={
          <Link href="/invoices/new" className="btn-primary">
            <Plus size={16} /> 請求書を作成
          </Link>
        }
      />

      {invoices.length === 0 ? (
        <EmptyState message="請求書がありません。「請求書を作成」から発行できます。" />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="border-b border-slate-100 bg-slate-50/60">
              <tr>
                <th className="th">番号</th>
                <th className="th">発行日</th>
                <th className="th">取引先</th>
                <th className="th">状態</th>
                <th className="th text-right">税抜</th>
                <th className="th text-right">消費税</th>
                <th className="th text-right">合計</th>
                <th className="th" />
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/50">
                  <td className="td font-medium tabular-nums">{inv.number}</td>
                  <td className="td whitespace-nowrap text-slate-500">{formatDate(inv.issueDate)}</td>
                  <td className="td">{inv.partnerId ? ptnName.get(inv.partnerId) : "—"}</td>
                  <td className="td">
                    <span className={`badge ${STATUS_TONE[inv.status]}`}>{INVOICE_STATUS[inv.status]}</span>
                  </td>
                  <td className="td text-right tabular-nums text-slate-500">{formatYen(inv.subtotal)}</td>
                  <td className="td text-right tabular-nums text-slate-500">{formatYen(inv.taxTotal)}</td>
                  <td className="td text-right tabular-nums font-semibold">{formatYen(inv.total)}</td>
                  <td className="td text-right">
                    <Link href={`/invoices/${inv.id}/edit`} className="text-slate-400 hover:text-brand-600">
                      <Pencil size={15} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
