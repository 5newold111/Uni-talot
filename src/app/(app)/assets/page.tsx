import { PageHeader } from "@/components/ui";
import { FixedAssetsManager } from "@/components/FixedAssetsManager";
import { listAccounts, listFixedAssets } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function AssetsPage() {
  const [assets, accounts] = await Promise.all([listFixedAssets(), listAccounts()]);
  const year = new Date().getFullYear();
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="固定資産・減価償却"
        description="定額法・一括償却・少額特例に対応。償却費は自動計算され、青色申告決算書に反映されます"
      />
      <FixedAssetsManager assets={assets} accounts={accounts} year={year} />
    </div>
  );
}
