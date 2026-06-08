// ドメイン操作の集約。UI(サーバーアクション/API)はここを経由してデータへアクセスする。
// マルチユーザー対応: 既定でセッションのログインユーザーにスコープする。
import { id } from "./data/ids";
import { getStore } from "./data/store";
import { seedAccountsForUser } from "./data/seed";
import { hashPassword } from "./auth";
import { getSessionUserId } from "./session";
import { summarizeInvoiceItems, taxFromGross } from "./accounting";
import { TAX_RATE_BY_CATEGORY, type TaxCategory } from "./constants";
import type {
  Account,
  Attachment,
  FixedAsset,
  Invoice,
  InvoiceItem,
  InvoiceWithItems,
  JournalLine,
  Partner,
  ShareLink,
  Transaction,
  TransactionWithLines,
  User,
} from "./types";

/** ログイン中のユーザーID。未認証なら例外。 */
function currentUserId(): string {
  const uid = getSessionUserId();
  if (!uid) throw new Error("未認証です。ログインしてください。");
  return uid;
}

export async function getBackendKind(): Promise<"sheets" | "memory"> {
  const store = await getStore();
  return store.kind;
}

// ---------------- Auth / User ----------------
export async function findUserByEmail(email: string): Promise<User | null> {
  const store = await getStore();
  const users = await store.list<User>("users");
  return users.find((u) => u.email.toLowerCase() === email.toLowerCase()) ?? null;
}

export async function getUserById(userId: string): Promise<User | null> {
  const store = await getStore();
  return (await store.list<User>("users")).find((u) => u.id === userId) ?? null;
}

/** 新規ユーザー登録＋標準勘定科目の投入。 */
export async function createUser(input: {
  email: string;
  name: string;
  password: string;
  businessName?: string;
}): Promise<User> {
  const store = await getStore();
  const existing = await findUserByEmail(input.email);
  if (existing) throw new Error("このメールアドレスは既に登録されています");
  const now = new Date().toISOString();
  const user: User = {
    id: id("user"),
    email: input.email,
    name: input.name,
    passwordHash: hashPassword(input.password),
    businessName: input.businessName ?? "",
    invoiceNumber: "",
    taxationType: "BLUE",
    consumptionTaxStatus: "EXEMPT",
    consumptionTaxMethod: "GENERAL",
    simplifiedBusinessType: null,
    fiscalYearStartMonth: 1,
    taxRounding: "FLOOR",
    blueDeduction: 650000,
    createdAt: now,
    updatedAt: now,
  };
  await store.insert("users", user);
  await seedAccountsForUser(store, user.id);
  return user;
}

export async function getCurrentUser(): Promise<User> {
  const store = await getStore();
  const uid = currentUserId();
  const u = (await store.list<User>("users")).find((x) => x.id === uid);
  if (!u) throw new Error("ユーザーが見つかりません");
  return u;
}

export async function updateUser(patch: Partial<User>): Promise<User> {
  const store = await getStore();
  const uid = currentUserId();
  // パスワードハッシュやIDは settings 経由で変更させない
  const { id: _id, passwordHash: _pw, ...safe } = patch;
  return store.update<User>("users", uid, {
    ...safe,
    updatedAt: new Date().toISOString(),
  });
}

// ---------------- Accounts ----------------
async function accountsForUser(userId: string): Promise<Account[]> {
  const store = await getStore();
  return (await store.list<Account>("accounts"))
    .filter((a) => a.userId === userId)
    .sort((a, b) => a.sortOrder - b.sortOrder || a.code.localeCompare(b.code));
}

export async function listAccounts(): Promise<Account[]> {
  return accountsForUser(currentUserId());
}

export async function listAccountsForUser(userId: string): Promise<Account[]> {
  return accountsForUser(userId);
}

export async function createAccount(
  input: Omit<Account, "id" | "userId" | "isSystem" | "sortOrder"> &
    Partial<Pick<Account, "sortOrder">>,
): Promise<Account> {
  const store = await getStore();
  const uid = currentUserId();
  const existing = await accountsForUser(uid);
  const acc: Account = {
    id: id("acc"),
    userId: uid,
    code: input.code,
    name: input.name,
    type: input.type,
    sortOrder: input.sortOrder ?? existing.length,
    defaultTaxCategory: input.defaultTaxCategory ?? null,
    isSystem: false,
    isActive: input.isActive ?? true,
  };
  return store.insert("accounts", acc);
}

export async function updateAccount(
  accountId: string,
  patch: Partial<Account>,
): Promise<Account> {
  const store = await getStore();
  return store.update<Account>("accounts", accountId, patch);
}

export async function deleteAccount(accountId: string): Promise<void> {
  const store = await getStore();
  const lines = await store.list<JournalLine>("journalLines");
  if (lines.some((l) => l.accountId === accountId)) {
    throw new Error("この科目は取引で使用されているため削除できません。無効化してください。");
  }
  await store.remove("accounts", accountId);
}

// ---------------- Partners ----------------
export async function listPartners(): Promise<Partner[]> {
  const store = await getStore();
  const uid = currentUserId();
  return (await store.list<Partner>("partners"))
    .filter((p) => p.userId === uid)
    .sort((a, b) => a.name.localeCompare(b.name, "ja"));
}

export async function createPartner(
  input: Omit<Partner, "id" | "userId">,
): Promise<Partner> {
  const store = await getStore();
  const p: Partner = { id: id("ptn"), userId: currentUserId(), ...input };
  return store.insert("partners", p);
}

export async function updatePartner(
  partnerId: string,
  patch: Partial<Partner>,
): Promise<Partner> {
  const store = await getStore();
  return store.update<Partner>("partners", partnerId, patch);
}

export async function deletePartner(partnerId: string): Promise<void> {
  const store = await getStore();
  await store.remove("partners", partnerId);
}

// ---------------- Transactions ----------------
export interface TxFilter {
  from?: string;
  to?: string;
  kind?: Transaction["kind"];
  partnerId?: string;
  accountId?: string;
}

async function txForUser(
  userId: string,
  filter: TxFilter = {},
): Promise<TransactionWithLines[]> {
  const store = await getStore();
  const [txs, allLines] = await Promise.all([
    store.list<Transaction>("transactions"),
    store.list<JournalLine>("journalLines"),
  ]);
  const linesByTx = new Map<string, JournalLine[]>();
  for (const l of allLines) {
    const arr = linesByTx.get(l.transactionId) ?? [];
    arr.push(l);
    linesByTx.set(l.transactionId, arr);
  }

  let result = txs
    .filter((t) => t.userId === userId)
    .map((t) => ({ ...t, lines: linesByTx.get(t.id) ?? [] }));

  if (filter.from) result = result.filter((t) => t.date >= filter.from!);
  if (filter.to) result = result.filter((t) => t.date <= filter.to!);
  if (filter.kind) result = result.filter((t) => t.kind === filter.kind);
  if (filter.partnerId)
    result = result.filter((t) => t.partnerId === filter.partnerId);
  if (filter.accountId)
    result = result.filter((t) =>
      t.lines.some((l) => l.accountId === filter.accountId),
    );

  return result.sort(
    (a, b) => b.date.localeCompare(a.date) || (b.slipNumber ?? 0) - (a.slipNumber ?? 0),
  );
}

export async function listTransactions(
  filter: TxFilter = {},
): Promise<TransactionWithLines[]> {
  return txForUser(currentUserId(), filter);
}

export async function listTransactionsForUser(
  userId: string,
  filter: TxFilter = {},
): Promise<TransactionWithLines[]> {
  return txForUser(userId, filter);
}

export async function getTransaction(
  txId: string,
): Promise<TransactionWithLines | null> {
  const store = await getStore();
  const uid = currentUserId();
  const tx = (await store.list<Transaction>("transactions")).find(
    (t) => t.id === txId && t.userId === uid,
  );
  if (!tx) return null;
  const lines = (await store.list<JournalLine>("journalLines")).filter(
    (l) => l.transactionId === txId,
  );
  return { ...tx, lines };
}

export interface LineInput {
  accountId: string;
  side: JournalLine["side"];
  amount: number;
  taxCategory: TaxCategory;
  description?: string;
}

export interface AttachmentInput {
  fileName: string;
  mimeType: string;
  dataUrl?: string;
  ocrText?: string;
}

export interface TransactionInput {
  date: string;
  description: string;
  partnerId?: string | null;
  kind: Transaction["kind"];
  note?: string;
  lines: LineInput[];
  attachments?: AttachmentInput[];
}

function buildLines(txId: string, inputs: LineInput[]): JournalLine[] {
  return inputs.map((li) => {
    const rate = TAX_RATE_BY_CATEGORY[li.taxCategory] ?? 0;
    return {
      id: id("jl"),
      transactionId: txId,
      accountId: li.accountId,
      side: li.side,
      amount: Math.round(li.amount),
      taxCategory: li.taxCategory,
      taxRate: rate,
      taxAmount: taxFromGross(Math.round(li.amount), li.taxCategory),
      description: li.description ?? "",
    };
  });
}

async function nextSlipNumber(
  store: Awaited<ReturnType<typeof getStore>>,
  userId: string,
): Promise<number> {
  const txs = (await store.list<Transaction>("transactions")).filter(
    (t) => t.userId === userId,
  );
  const max = txs.reduce((m, t) => Math.max(m, t.slipNumber ?? 0), 0);
  return max + 1;
}

async function saveAttachments(
  store: Awaited<ReturnType<typeof getStore>>,
  userId: string,
  txId: string,
  attachments: AttachmentInput[] | undefined,
) {
  if (!attachments || attachments.length === 0) return;
  const now = new Date().toISOString();
  const rows: Attachment[] = attachments.map((a) => ({
    id: id("att"),
    userId,
    transactionId: txId,
    fileName: a.fileName,
    mimeType: a.mimeType,
    dataUrl: a.dataUrl ?? "",
    ocrText: a.ocrText ?? "",
    createdAt: now,
  }));
  await store.insertMany("attachments", rows);
}

export async function createTransaction(
  input: TransactionInput,
): Promise<TransactionWithLines> {
  const store = await getStore();
  const uid = currentUserId();
  const now = new Date().toISOString();
  const txId = id("tx");
  const tx: Transaction = {
    id: txId,
    userId: uid,
    date: input.date,
    description: input.description,
    partnerId: input.partnerId ?? null,
    kind: input.kind,
    slipNumber: await nextSlipNumber(store, uid),
    note: input.note ?? "",
    createdAt: now,
    updatedAt: now,
  };
  const lines = buildLines(txId, input.lines);
  await store.insert("transactions", tx);
  await store.insertMany("journalLines", lines);
  await saveAttachments(store, uid, txId, input.attachments);
  return { ...tx, lines };
}

export async function updateTransaction(
  txId: string,
  input: TransactionInput,
): Promise<TransactionWithLines> {
  const store = await getStore();
  const uid = currentUserId();
  const existing = (await store.list<JournalLine>("journalLines")).filter(
    (l) => l.transactionId === txId,
  );
  for (const l of existing) await store.remove("journalLines", l.id);

  const updated = await store.update<Transaction>("transactions", txId, {
    date: input.date,
    description: input.description,
    partnerId: input.partnerId ?? null,
    kind: input.kind,
    note: input.note ?? "",
    updatedAt: new Date().toISOString(),
  });
  const lines = buildLines(txId, input.lines);
  await store.insertMany("journalLines", lines);
  await saveAttachments(store, uid, txId, input.attachments);
  return { ...updated, lines };
}

export async function deleteTransaction(txId: string): Promise<void> {
  const store = await getStore();
  const lines = (await store.list<JournalLine>("journalLines")).filter(
    (l) => l.transactionId === txId,
  );
  for (const l of lines) await store.remove("journalLines", l.id);
  const atts = (await store.list<Attachment>("attachments")).filter(
    (a) => a.transactionId === txId,
  );
  for (const a of atts) await store.remove("attachments", a.id);
  await store.remove("transactions", txId);
}

export async function listAttachments(txId: string): Promise<Attachment[]> {
  const store = await getStore();
  return (await store.list<Attachment>("attachments")).filter(
    (a) => a.transactionId === txId,
  );
}

// ---------------- Invoices ----------------
export async function listInvoices(): Promise<Invoice[]> {
  const store = await getStore();
  const uid = currentUserId();
  return (await store.list<Invoice>("invoices"))
    .filter((i) => i.userId === uid)
    .sort((a, b) => b.issueDate.localeCompare(a.issueDate));
}

export async function getInvoice(
  invoiceId: string,
): Promise<InvoiceWithItems | null> {
  const store = await getStore();
  const uid = currentUserId();
  const inv = (await store.list<Invoice>("invoices")).find(
    (i) => i.id === invoiceId && i.userId === uid,
  );
  if (!inv) return null;
  const items = (await store.list<InvoiceItem>("invoiceItems"))
    .filter((it) => it.invoiceId === invoiceId)
    .sort((a, b) => a.sortOrder - b.sortOrder);
  return { ...inv, items };
}

export interface InvoiceItemInput {
  description: string;
  quantity: number;
  unitPrice: number;
  taxCategory: TaxCategory;
}

export interface InvoiceInput {
  partnerId?: string | null;
  number: string;
  issueDate: string;
  dueDate?: string | null;
  status: Invoice["status"];
  note?: string;
  items: InvoiceItemInput[];
}

export async function nextInvoiceNumber(): Promise<string> {
  const invoices = await listInvoices();
  const year = new Date().getFullYear();
  const seq = invoices.length + 1;
  return `INV-${year}-${String(seq).padStart(4, "0")}`;
}

export async function createInvoice(
  input: InvoiceInput,
): Promise<InvoiceWithItems> {
  const store = await getStore();
  const user = await getCurrentUser();
  const now = new Date().toISOString();
  const invId = id("inv");
  const summary = summarizeInvoiceItems(input.items, user.taxRounding);
  const inv: Invoice = {
    id: invId,
    userId: user.id,
    partnerId: input.partnerId ?? null,
    number: input.number,
    issueDate: input.issueDate,
    dueDate: input.dueDate ?? null,
    status: input.status,
    subtotal: summary.subtotal,
    taxTotal: summary.taxTotal,
    total: summary.total,
    note: input.note ?? "",
    createdAt: now,
    updatedAt: now,
  };
  const items: InvoiceItem[] = input.items.map((it, i) => ({
    id: id("ii"),
    invoiceId: invId,
    description: it.description,
    quantity: it.quantity,
    unitPrice: it.unitPrice,
    taxCategory: it.taxCategory,
    taxRate: TAX_RATE_BY_CATEGORY[it.taxCategory] ?? 0,
    sortOrder: i,
  }));
  await store.insert("invoices", inv);
  await store.insertMany("invoiceItems", items);
  return { ...inv, items };
}

export async function updateInvoice(
  invoiceId: string,
  input: InvoiceInput,
): Promise<InvoiceWithItems> {
  const store = await getStore();
  const user = await getCurrentUser();
  const existing = (await store.list<InvoiceItem>("invoiceItems")).filter(
    (it) => it.invoiceId === invoiceId,
  );
  for (const it of existing) await store.remove("invoiceItems", it.id);

  const summary = summarizeInvoiceItems(input.items, user.taxRounding);
  const inv = await store.update<Invoice>("invoices", invoiceId, {
    partnerId: input.partnerId ?? null,
    number: input.number,
    issueDate: input.issueDate,
    dueDate: input.dueDate ?? null,
    status: input.status,
    subtotal: summary.subtotal,
    taxTotal: summary.taxTotal,
    total: summary.total,
    note: input.note ?? "",
    updatedAt: new Date().toISOString(),
  });
  const items: InvoiceItem[] = input.items.map((it, i) => ({
    id: id("ii"),
    invoiceId,
    description: it.description,
    quantity: it.quantity,
    unitPrice: it.unitPrice,
    taxCategory: it.taxCategory,
    taxRate: TAX_RATE_BY_CATEGORY[it.taxCategory] ?? 0,
    sortOrder: i,
  }));
  await store.insertMany("invoiceItems", items);
  return { ...inv, items };
}

export async function deleteInvoice(invoiceId: string): Promise<void> {
  const store = await getStore();
  const items = (await store.list<InvoiceItem>("invoiceItems")).filter(
    (it) => it.invoiceId === invoiceId,
  );
  for (const it of items) await store.remove("invoiceItems", it.id);
  await store.remove("invoices", invoiceId);
}

// ---------------- Fixed assets ----------------
export async function listFixedAssets(): Promise<FixedAsset[]> {
  const store = await getStore();
  const uid = currentUserId();
  return (await store.list<FixedAsset>("fixedAssets"))
    .filter((a) => a.userId === uid)
    .sort((a, b) => a.acquisitionDate.localeCompare(b.acquisitionDate));
}

export async function createFixedAsset(
  input: Omit<FixedAsset, "id" | "userId" | "createdAt">,
): Promise<FixedAsset> {
  const store = await getStore();
  const asset: FixedAsset = {
    id: id("fa"),
    userId: currentUserId(),
    createdAt: new Date().toISOString(),
    ...input,
  };
  return store.insert("fixedAssets", asset);
}

export async function updateFixedAsset(
  assetId: string,
  patch: Partial<FixedAsset>,
): Promise<FixedAsset> {
  const store = await getStore();
  return store.update<FixedAsset>("fixedAssets", assetId, patch);
}

export async function deleteFixedAsset(assetId: string): Promise<void> {
  const store = await getStore();
  await store.remove("fixedAssets", assetId);
}

// ---------------- Share links ----------------
export async function listShareLinks(): Promise<ShareLink[]> {
  const store = await getStore();
  const uid = currentUserId();
  return (await store.list<ShareLink>("shareLinks"))
    .filter((s) => s.userId === uid)
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export async function createShareLink(
  input: Pick<ShareLink, "label" | "scope" | "fiscalYear" | "expiresAt">,
): Promise<ShareLink> {
  const store = await getStore();
  const { token } = await import("./data/ids");
  const link: ShareLink = {
    id: id("shr"),
    userId: currentUserId(),
    token: token(),
    label: input.label ?? "",
    scope: input.scope,
    fiscalYear: input.fiscalYear ?? null,
    expiresAt: input.expiresAt ?? null,
    revokedAt: null,
    createdAt: new Date().toISOString(),
  };
  return store.insert("shareLinks", link);
}

export async function getShareLinkByToken(
  token: string,
): Promise<ShareLink | null> {
  const store = await getStore();
  const link = (await store.list<ShareLink>("shareLinks")).find(
    (s) => s.token === token,
  );
  if (!link || link.revokedAt) return null;
  if (link.expiresAt && link.expiresAt < new Date().toISOString()) return null;
  return link;
}

export async function revokeShareLink(linkId: string): Promise<void> {
  const store = await getStore();
  await store.update<ShareLink>("shareLinks", linkId, {
    revokedAt: new Date().toISOString(),
  });
}
