import { PageHeader } from "@/components/ui";
import { SettingsForm } from "@/components/SettingsForm";
import { getBackendKind, getCurrentUser } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const [user, backend] = await Promise.all([getCurrentUser(), getBackendKind()]);
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="設定" description="事業者情報と税区分の初期値を設定します" />
      <div className="mb-4 card p-4 text-sm">
        <span className="font-medium text-slate-600">データ保存先：</span>{" "}
        {backend === "sheets" ? (
          <span className="badge bg-emerald-50 text-emerald-700">Google スプレッドシート</span>
        ) : (
          <span className="badge bg-amber-50 text-amber-700">インメモリ（デモ）</span>
        )}
      </div>
      <SettingsForm user={user} />
    </div>
  );
}
