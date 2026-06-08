// 個人事業主（青色申告）向けの標準勘定科目テンプレート。
// セットアップ時に投入する。code は一般的な慣習に概ね沿った採番。
import type { AccountType, TaxCategory } from "./constants";

export interface AccountSeed {
  code: string;
  name: string;
  type: AccountType;
  defaultTaxCategory?: TaxCategory;
}

export const DEFAULT_ACCOUNTS: AccountSeed[] = [
  // 資産
  { code: "101", name: "現金", type: "ASSET" },
  { code: "102", name: "普通預金", type: "ASSET" },
  { code: "103", name: "事業主貸", type: "ASSET" },
  { code: "111", name: "売掛金", type: "ASSET" },
  { code: "112", name: "未収入金", type: "ASSET" },
  { code: "121", name: "前払金", type: "ASSET" },
  { code: "131", name: "工具器具備品", type: "ASSET" },

  // 負債
  { code: "201", name: "買掛金", type: "LIABILITY" },
  { code: "202", name: "未払金", type: "LIABILITY" },
  { code: "203", name: "前受金", type: "LIABILITY" },
  { code: "204", name: "預り金", type: "LIABILITY" },
  { code: "205", name: "未払消費税", type: "LIABILITY" },

  // 純資産
  { code: "301", name: "元入金", type: "EQUITY" },
  { code: "302", name: "事業主借", type: "EQUITY" },

  // 収益
  { code: "401", name: "売上高", type: "REVENUE", defaultTaxCategory: "TAXABLE_10" },
  { code: "402", name: "雑収入", type: "REVENUE", defaultTaxCategory: "OUT_OF_SCOPE" },

  // 費用（経費）
  { code: "501", name: "仕入高", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "511", name: "租税公課", type: "EXPENSE", defaultTaxCategory: "OUT_OF_SCOPE" },
  { code: "512", name: "荷造運賃", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "513", name: "水道光熱費", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "514", name: "旅費交通費", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "515", name: "通信費", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "516", name: "広告宣伝費", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "517", name: "接待交際費", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "518", name: "損害保険料", type: "EXPENSE", defaultTaxCategory: "OUT_OF_SCOPE" },
  { code: "519", name: "修繕費", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "520", name: "消耗品費", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "521", name: "減価償却費", type: "EXPENSE", defaultTaxCategory: "OUT_OF_SCOPE" },
  { code: "522", name: "福利厚生費", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "523", name: "給料賃金", type: "EXPENSE", defaultTaxCategory: "OUT_OF_SCOPE" },
  { code: "524", name: "外注工賃", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "525", name: "利子割引料", type: "EXPENSE", defaultTaxCategory: "OUT_OF_SCOPE" },
  { code: "526", name: "地代家賃", type: "EXPENSE", defaultTaxCategory: "OUT_OF_SCOPE" },
  { code: "527", name: "支払手数料", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "528", name: "新聞図書費", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "529", name: "会議費", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
  { code: "530", name: "諸会費", type: "EXPENSE", defaultTaxCategory: "OUT_OF_SCOPE" },
  { code: "590", name: "雑費", type: "EXPENSE", defaultTaxCategory: "TAXABLE_10" },
];
