import { notFound } from "next/navigation";
import { PageHeader } from "@/components/ui";
import { TransactionForm } from "@/components/TransactionForm";
import { getTransaction, listAccounts, listPartners } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function EditTransactionPage({
  params,
}: {
  params: { id: string };
}) {
  const [tx, accounts, partners] = await Promise.all([
    getTransaction(params.id),
    listAccounts(),
    listPartners(),
  ]);
  if (!tx) notFound();
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="取引を編集" description={`伝票番号 #${tx.slipNumber ?? "-"}`} />
      <TransactionForm accounts={accounts} partners={partners} initial={tx} />
    </div>
  );
}
