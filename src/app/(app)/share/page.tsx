import { headers } from "next/headers";
import { PageHeader } from "@/components/ui";
import { ShareManager } from "@/components/ShareManager";
import { listShareLinks } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function SharePage() {
  const links = await listShareLinks();
  const h = headers();
  const host = h.get("host") ?? "localhost:3000";
  const proto = h.get("x-forwarded-proto") ?? "http";
  const baseUrl = `${proto}://${host}`;

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="税理士共有"
        description="閲覧用リンクを発行して、帳簿・レポートを税理士と共有できます"
      />
      <div className="mb-4 card p-4 text-sm text-slate-600">
        共有リンクを開くと、対象年度の損益計算書・仕訳帳を<strong>閲覧のみ</strong>で確認できます。
        スプレッドシート連携時は、シートを税理士のGoogleアカウントに直接共有することも可能です。
      </div>
      <ShareManager links={links} baseUrl={baseUrl} />
    </div>
  );
}
