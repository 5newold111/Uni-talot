// 表示用フォーマッタ（クライアント/サーバー共通・副作用なし）。

const yen = new Intl.NumberFormat("ja-JP");

/** 1234567 -> "¥1,234,567" */
export function formatYen(n: number): string {
  const sign = n < 0 ? "-" : "";
  return `${sign}¥${yen.format(Math.abs(Math.round(n)))}`;
}

/** 1234567 -> "1,234,567" */
export function formatNumber(n: number): string {
  return yen.format(Math.round(n));
}

/** "2026-06-08" -> "2026/06/08" */
export function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, "0")}/${String(
    d.getDate(),
  ).padStart(2, "0")}`;
}

export function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate(),
  ).padStart(2, "0")}`;
}
