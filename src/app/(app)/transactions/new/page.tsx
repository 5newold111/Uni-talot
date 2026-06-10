import { PageHeader } from "@/components/ui";
import { TransactionForm } from "@/components/TransactionForm";
import { listAccounts, listPartners } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function NewTransactionPage() {
  const [accounts, partners] = await Promise.all([listAccounts(), listPartners()]);
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="取引を入力" description="経費・売上は簡単入力、複雑な仕訳は詳細モードで" />
      <TransactionForm accounts={accounts} partners={partners} />
    </div>
  );
}
