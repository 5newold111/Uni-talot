"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookText,
  Building2,
  FileText,
  LayoutDashboard,
  ListTree,
  PieChart,
  Receipt,
  Settings,
  Share2,
} from "lucide-react";

const NAV = [
  { href: "/", label: "ダッシュボード", icon: LayoutDashboard },
  { href: "/transactions", label: "取引・仕訳", icon: BookText },
  { href: "/invoices", label: "請求書", icon: FileText },
  { href: "/partners", label: "取引先", icon: Building2 },
  { href: "/accounts", label: "勘定科目", icon: ListTree },
  { href: "/reports", label: "レポート", icon: PieChart },
  { href: "/share", label: "税理士共有", icon: Share2 },
  { href: "/settings", label: "設定", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

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
      <nav className="flex-1 space-y-0.5 px-3">
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
      <div className="px-5 py-4 text-[11px] text-slate-400">
        青色申告・インボイス対応
      </div>
    </aside>
  );
}
