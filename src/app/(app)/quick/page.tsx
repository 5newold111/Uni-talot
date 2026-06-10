import { PageHeader } from "@/components/ui";
import { QuickEntry } from "@/components/QuickEntry";
import { listAccounts, listPartners } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function QuickEntryPage() {
  const [accounts, partners] = await Promise.all([listAccounts(), listPartners()]);
  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="かんたん入力"
        description="経費・売上を素早く連続入力。リストに溜めてまとめて保存できます（スマホ対応）"
      />
      <QuickEntry accounts={accounts} partners={partners} />
    </div>
  );
}
