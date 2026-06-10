import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "会計フリー帳 | 個人事業主の財務管理",
  description: "経費・売上の記帳、請求書、青色申告・インボイス対応の財務管理システム",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
