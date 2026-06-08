// 減価償却の計算（純粋関数）。個人事業主（暦年: 1〜12月）を前提とする。
//
// 対応:
//  - STRAIGHT_LINE 定額法（月割・備忘価額¥1まで）
//  - LUMP_3YEAR    一括償却資産（取得価額の1/3を3年均等、残存0）
//  - IMMEDIATE     少額減価償却資産の特例（取得年に全額償却、残存0）
//
// 注: 事業専用割合(businessRatio)は「必要経費算入額(expense)」に乗じる。
//     税務上の償却額(depreciation)・帳簿価額(bookValue)は満額ベース。
import type { FixedAsset } from "./types";

export interface DepreciationYear {
  year: number;
  /** その年の事業供用月数 */
  months: number;
  /** その年の償却額（満額） */
  depreciation: number;
  /** 必要経費算入額（償却額 × 事業割合） */
  expense: number;
  /** 期末減価償却累計額 */
  accumulated: number;
  /** 期末帳簿価額 */
  bookValue: number;
}

const MAX_YEARS = 100;

function monthOf(dateIso: string): number {
  const m = new Date(dateIso).getMonth() + 1;
  return Number.isFinite(m) && m >= 1 && m <= 12 ? m : 1;
}
function yearOf(dateIso: string): number {
  const y = new Date(dateIso).getFullYear();
  return Number.isFinite(y) ? y : new Date().getFullYear();
}

/** 減価償却スケジュール（取得年から償却完了まで）。 */
export function depreciationSchedule(
  asset: Pick<
    FixedAsset,
    "acquisitionCost" | "usefulLife" | "method" | "startDate" | "businessRatio"
  >,
): DepreciationYear[] {
  const cost = Math.max(0, Math.round(asset.acquisitionCost));
  const ratio = asset.businessRatio > 0 ? asset.businessRatio : 100;
  const startYear = yearOf(asset.startDate);
  const startMonth = monthOf(asset.startDate);
  const rows: DepreciationYear[] = [];
  const expenseOf = (dep: number) => Math.floor((dep * ratio) / 100);

  if (cost === 0) return rows;

  if (asset.method === "IMMEDIATE") {
    rows.push({
      year: startYear,
      months: 12 - startMonth + 1,
      depreciation: cost,
      expense: expenseOf(cost),
      accumulated: cost,
      bookValue: 0,
    });
    return rows;
  }

  if (asset.method === "LUMP_3YEAR") {
    const per = Math.floor(cost / 3);
    let acc = 0;
    for (let i = 0; i < 3; i++) {
      const dep = i === 2 ? cost - acc : per; // 最終年で端数調整
      acc += dep;
      rows.push({
        year: startYear + i,
        months: 12,
        depreciation: dep,
        expense: expenseOf(dep),
        accumulated: acc,
        bookValue: cost - acc,
      });
    }
    return rows;
  }

  // STRAIGHT_LINE 定額法
  const life = Math.max(1, Math.floor(asset.usefulLife));
  const annual = Math.floor(cost / life); // 年間の満額償却
  let acc = 0;
  let book = cost;
  for (let i = 0; i < MAX_YEARS; i++) {
    const year = startYear + i;
    const months = i === 0 ? 12 - startMonth + 1 : 12;
    let dep = i === 0 ? Math.floor((annual * months) / 12) : annual;
    if (dep <= 0) dep = 1;
    // 備忘価額 ¥1 を残す
    if (book - dep <= 1) dep = book - 1;
    if (dep <= 0) break;
    acc += dep;
    book -= dep;
    rows.push({
      year,
      months,
      depreciation: dep,
      expense: expenseOf(dep),
      accumulated: acc,
      bookValue: book,
    });
    if (book <= 1) break;
  }
  return rows;
}

/** 指定年の償却額・必要経費算入額・期末帳簿価額。該当が無ければ0。 */
export function depreciationForYear(
  asset: Pick<
    FixedAsset,
    "acquisitionCost" | "usefulLife" | "method" | "startDate" | "businessRatio"
  >,
  year: number,
): { depreciation: number; expense: number; bookValue: number } {
  const schedule = depreciationSchedule(asset);
  const row = schedule.find((r) => r.year === year);
  if (row) {
    return { depreciation: row.depreciation, expense: row.expense, bookValue: row.bookValue };
  }
  // 償却完了後（簿価のみ）
  const last = schedule[schedule.length - 1];
  if (last && year > last.year) {
    return { depreciation: 0, expense: 0, bookValue: last.bookValue };
  }
  // 取得前
  return { depreciation: 0, expense: 0, bookValue: 0 };
}
