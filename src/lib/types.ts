// ドメイン型。Sheets/InMemory どちらのアダプタも同じ型を読み書きする。
import type {
  AccountType,
  ConsumptionTaxMethod,
  ConsumptionTaxStatus,
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
  businessName?: string;
  invoiceNumber?: string;
  taxationType: TaxationType;
  consumptionTaxStatus: ConsumptionTaxStatus;
  consumptionTaxMethod: ConsumptionTaxMethod;
  simplifiedBusinessType?: number | null;
  fiscalYearStartMonth: number;
  taxRounding: TaxRounding;
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
