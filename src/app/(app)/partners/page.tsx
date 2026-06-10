import { PageHeader } from "@/components/ui";
import { PartnersManager } from "@/components/PartnersManager";
import { listPartners } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function PartnersPage() {
  const partners = await listPartners();
  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="取引先"
        description="得意先・仕入先を登録。インボイス番号は仕入税額控除の判定に使えます"
      />
      <PartnersManager partners={partners} />
    </div>
  );
}
