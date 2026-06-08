import { Sidebar } from "@/components/Sidebar";
import { getBackendKind } from "@/lib/repo";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const backend = await getBackendKind();

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        {backend === "memory" && (
          <div className="bg-amber-50 px-6 py-1.5 text-center text-xs text-amber-800">
            デモモード（インメモリ）で動作中。Google スプレッドシート連携を有効にするには
            <code className="mx-1 rounded bg-amber-100 px-1">.env</code>
            に認証情報を設定してください。
          </div>
        )}
        <main className="flex-1 px-6 py-6">{children}</main>
      </div>
    </div>
  );
}
