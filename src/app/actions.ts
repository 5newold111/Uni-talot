"use server";

import { revalidatePath } from "next/cache";
import {
  createAccount,
  createInvoice,
  createPartner,
  createShareLink,
  createTransaction,
  deleteAccount,
  deleteInvoice,
  deletePartner,
  deleteTransaction,
  revokeShareLink,
  updateAccount,
  updateInvoice,
  updatePartner,
  updateTransaction,
  updateUser,
  type InvoiceInput,
  type TransactionInput,
} from "@/lib/repo";
import type { Account, Partner, ShareLink, User } from "@/lib/types";

type Result = { ok: true } | { ok: false; error: string };

function fail(e: unknown): Result {
  return { ok: false, error: e instanceof Error ? e.message : "エラーが発生しました" };
}

// ---- Transactions ----
export async function saveTransactionAction(
  input: TransactionInput,
  id?: string,
): Promise<Result> {
  try {
    if (id) await updateTransaction(id, input);
    else await createTransaction(input);
    revalidatePath("/transactions");
    revalidatePath("/");
    revalidatePath("/reports");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

export async function deleteTransactionAction(id: string): Promise<Result> {
  try {
    await deleteTransaction(id);
    revalidatePath("/transactions");
    revalidatePath("/");
    revalidatePath("/reports");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

// ---- Accounts ----
export async function saveAccountAction(
  input: Omit<Account, "id" | "userId" | "isSystem" | "sortOrder">,
  id?: string,
): Promise<Result> {
  try {
    if (id) await updateAccount(id, input);
    else await createAccount(input);
    revalidatePath("/accounts");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

export async function deleteAccountAction(id: string): Promise<Result> {
  try {
    await deleteAccount(id);
    revalidatePath("/accounts");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

// ---- Partners ----
export async function savePartnerAction(
  input: Omit<Partner, "id" | "userId">,
  id?: string,
): Promise<Result> {
  try {
    if (id) await updatePartner(id, input);
    else await createPartner(input);
    revalidatePath("/partners");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

export async function deletePartnerAction(id: string): Promise<Result> {
  try {
    await deletePartner(id);
    revalidatePath("/partners");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

// ---- Invoices ----
export async function saveInvoiceAction(
  input: InvoiceInput,
  id?: string,
): Promise<Result> {
  try {
    if (id) await updateInvoice(id, input);
    else await createInvoice(input);
    revalidatePath("/invoices");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

export async function deleteInvoiceAction(id: string): Promise<Result> {
  try {
    await deleteInvoice(id);
    revalidatePath("/invoices");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

// ---- Settings ----
export async function saveSettingsAction(patch: Partial<User>): Promise<Result> {
  try {
    await updateUser(patch);
    revalidatePath("/settings");
    revalidatePath("/");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

// ---- Share links ----
export async function createShareLinkAction(
  input: Pick<ShareLink, "label" | "scope" | "fiscalYear" | "expiresAt">,
): Promise<Result> {
  try {
    await createShareLink(input);
    revalidatePath("/share");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

export async function revokeShareLinkAction(id: string): Promise<Result> {
  try {
    await revokeShareLink(id);
    revalidatePath("/share");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}
