"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BookText,
  Building2,
  FileSpreadsheet,
  FileText,
  Landmark,
  LayoutDashboard,
  ListTree,
  LogOut,
  PieChart,
  Receipt,
  Settings,
  Share2,
  Zap,
} from "lucide-react";
import { logoutAction } from "@/app/actions";

const NAV = [
  { href: "/", label: "ダッシュボード", icon: LayoutDashboard },
  { href: "/quick", label: "かんたん入力", icon: Zap },
  { href: "/transactions", label: "取引・仕訳", icon: BookText },
  { href: "/invoices", label: "請求書", icon: FileText },
  { href: "/partners", label: "取引先", icon: Building2 },
  { href: "/accounts", label: "勘定科目", icon: ListTree },
  { href: "/assets", label: "固定資産・減価償却", icon: Landmark },
  { href: "/reports", label: "レポート", icon: PieChart },
  { href: "/reports/blue-return", label: "青色申告決算書", icon: FileSpreadsheet },
  { href: "/share", label: "税理士共有", icon: Share2 },
  { href: "/settings", label: "設定", icon: Settings },
];

export function Sidebar({ userName, email }: { userName: string; email: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const isActive = (href: string) =>
    href === "/"
      ? pathname === "/"
      : href === "/reports"
        ? pathname === "/reports"
        : pathname.startsWith(href);

  async function logout() {
    await logoutAction();
    router.push("/login");
    router.refresh();
  }

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white">
          <Receipt size={20} />
        </div>
        <div>
          <div className="text-sm font-bold leading-tight">会計フリー帳</div>
          <div className="text-[11px] text-slate-400">個人事業主の財務管理</div>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActive(href)
                ? "bg-brand-50 text-brand-700"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>
      <div className="border-t border-slate-100 px-4 py-3">
        <div className="truncate text-sm font-medium text-slate-700">{userName}</div>
        <div className="truncate text-[11px] text-slate-400">{email}</div>
        <button
          onClick={logout}
          className="mt-2 flex items-center gap-2 text-xs font-medium text-slate-500 hover:text-red-600"
        >
          <LogOut size={14} /> ログアウト
        </button>
      </div>
    </aside>
  );
}
