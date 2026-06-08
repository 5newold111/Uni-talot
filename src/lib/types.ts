// ドメイン型。Sheets/InMemory どちらのアダプタも同じ型を読み書きする。
import type {
  AccountType,
  ConsumptionTaxMethod,
  ConsumptionTaxStatus,
  DepreciationMethod,
  InvoiceStatus,
  PartnerType,
  ShareScope,
  Side,
  TaxCategory,
  TaxationType,
  TaxRounding,
  TxKind,
} from "./constants";

export interface User {
  id: string;
  email: string;
  name: string;
  /** scrypt によるパスワードハッシュ（"salt:hash" 形式） */
  passwordHash?: string;
  businessName?: string;
  invoiceNumber?: string;
  taxationType: TaxationType;
  consumptionTaxStatus: ConsumptionTaxStatus;
  consumptionTaxMethod: ConsumptionTaxMethod;
  simplifiedBusinessType?: number | null;
  fiscalYearStartMonth: number;
  taxRounding: TaxRounding;
  /** 青色申告特別控除額（円） */
  blueDeduction: number;
  createdAt: string;
  updatedAt: string;
}

export interface Account {
  id: string;
  userId: string;
  code: string;
  name: string;
  type: AccountType;
  sortOrder: number;
  defaultTaxCategory?: TaxCategory | null;
  isSystem: boolean;
  isActive: boolean;
}

export interface Partner {
  id: string;
  userId: string;
  name: string;
  type: PartnerType;
  invoiceNumber?: string;
  email?: string;
  phone?: string;
  address?: string;
  note?: string;
}

export interface JournalLine {
  id: string;
  transactionId: string;
  accountId: string;
  side: Side;
  amount: number; // 税込・円
  taxCategory: TaxCategory;
  taxRate: number;
  taxAmount: number;
  description?: string;
}

export interface Transaction {
  id: string;
  userId: string;
  date: string; // ISO (YYYY-MM-DD)
  description: string;
  partnerId?: string | null;
  kind: TxKind;
  slipNumber?: number | null;
  note?: string;
  createdAt: string;
  updatedAt: string;
}

export interface TransactionWithLines extends Transaction {
  lines: JournalLine[];
}

export interface Invoice {
  id: string;
  userId: string;
  partnerId?: string | null;
  number: string;
  issueDate: string;
  dueDate?: string | null;
  status: InvoiceStatus;
  subtotal: number;
  taxTotal: number;
  total: number;
  note?: string;
  createdAt: string;
  updatedAt: string;
}

export interface InvoiceItem {
  id: string;
  invoiceId: string;
  description: string;
  quantity: number;
  unitPrice: number; // 税抜・円
  taxCategory: TaxCategory;
  taxRate: number;
  sortOrder: number;
}

export interface InvoiceWithItems extends Invoice {
  items: InvoiceItem[];
}

export interface Attachment {
  id: string;
  userId: string;
  transactionId: string;
  fileName: string;
  mimeType: string;
  /** 小容量画像の data URL（縮小済み）。OCRテキストは ocrText に保持 */
  dataUrl?: string;
  ocrText?: string;
  createdAt: string;
}

export interface FixedAsset {
  id: string;
  userId: string;
  name: string;
  /** 取得年月日 (YYYY-MM-DD) */
  acquisitionDate: string;
  /** 事業供用開始年月日 */
  startDate: string;
  /** 取得価額（円） */
  acquisitionCost: number;
  /** 耐用年数（年）。一括償却は3固定、即時償却は不要 */
  usefulLife: number;
  method: DepreciationMethod;
  /** 事業専用割合(%)。家事按分。既定100 */
  businessRatio: number;
  /** 対応する資産勘定科目ID（任意） */
  accountId?: string | null;
  note?: string;
  createdAt: string;
}

export interface ShareLink {
  id: string;
  userId: string;
  token: string;
  label?: string;
  scope: ShareScope;
  fiscalYear?: number | null;
  expiresAt?: string | null;
  revokedAt?: string | null;
  createdAt: string;
}
