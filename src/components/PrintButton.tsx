"use client";

import { Printer } from "lucide-react";

export function PrintButton({ label = "印刷 / PDF保存" }: { label?: string }) {
  return (
    <button className="btn-secondary print:hidden" onClick={() => window.print()}>
      <Printer size={16} /> {label}
    </button>
  );
}
