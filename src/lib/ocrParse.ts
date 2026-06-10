// 領収書OCRテキストから日付・金額を推定する（純粋関数・テスト対象）。

/** "2026/06/08" / "2026年6月8日" / "2026-6-8" 等を ISO(YYYY-MM-DD) に。 */
export function extractDate(text: string): string | null {
  const m = text.match(/(20\d{2})\s*[年./\-]\s*(\d{1,2})\s*[月./\-]\s*(\d{1,2})/);
  if (!m) return null;
  const [, y, mo, d] = m;
  const month = Number(mo);
  const day = Number(d);
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  return `${y}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function parseNumber(raw: string): number | null {
  const n = Number(raw.replace(/[,，\s]/g, ""));
  return Number.isFinite(n) && n > 0 ? Math.round(n) : null;
}

/**
 * 合計金額を推定する。
 * 「合計 / 総額 / お会計 / お支払 / total」を含む行の数値を優先し、
 * 見つからなければ全体の最大金額を採用する。
 */
export function extractAmount(text: string): number | null {
  const lines = text.split(/\r?\n/);
  const keyword = /(合\s*計|総\s*額|お会計|お支払|請求|total|amount)/i;
  const numberPat = /[¥￥]?\s*([0-9０-９][0-9０-９,，]{1,})\s*円?/g;

  const toHankaku = (s: string) =>
    s.replace(/[０-９]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0));

  // 1) キーワード行の数値を優先
  const candidates: number[] = [];
  for (const line of lines) {
    if (!keyword.test(line)) continue;
    const nums = [...toHankaku(line).matchAll(numberPat)]
      .map((mm) => parseNumber(mm[1]))
      .filter((v): v is number => v !== null);
    candidates.push(...nums);
  }
  if (candidates.length > 0) return Math.max(...candidates);

  // 2) フォールバック: 全体の最大金額
  const all = [...toHankaku(text).matchAll(numberPat)]
    .map((mm) => parseNumber(mm[1]))
    .filter((v): v is number => v !== null);
  return all.length > 0 ? Math.max(...all) : null;
}

export interface OcrResult {
  date: string | null;
  amount: number | null;
}

export function parseReceipt(text: string): OcrResult {
  return { date: extractDate(text), amount: extractAmount(text) };
}
