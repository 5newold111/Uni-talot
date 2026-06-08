import { PageHeader } from "@/components/ui";
import { AccountsManager } from "@/components/AccountsManager";
import { listAccounts } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function AccountsPage() {
  const accounts = await listAccounts();
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="勘定科目"
        description="標準科目に加え、事業に合わせて科目を追加できます"
      />
      <AccountsManager accounts={accounts} />
    </div>
  );
}
