"use server";

import { revalidatePath } from "next/cache";
import {
  createAccount,
  createFixedAsset,
  createInvoice,
  createPartner,
  createShareLink,
  createTransaction,
  createUser,
  deleteAccount,
  deleteFixedAsset,
  deleteInvoice,
  deletePartner,
  deleteTransaction,
  findUserByEmail,
  revokeShareLink,
  updateAccount,
  updateFixedAsset,
  updateInvoice,
  updatePartner,
  updateTransaction,
  updateUser,
  type InvoiceInput,
  type TransactionInput,
} from "@/lib/repo";
import { verifyPassword } from "@/lib/auth";
import { clearSessionCookie, setSessionCookie } from "@/lib/session";
import type { Account, FixedAsset, Partner, ShareLink, User } from "@/lib/types";

type Result = { ok: true } | { ok: false; error: string };

function fail(e: unknown): Result {
  return { ok: false, error: e instanceof Error ? e.message : "エラーが発生しました" };
}

// ---- Auth ----
export async function registerAction(input: {
  email: string;
  name: string;
  password: string;
  businessName?: string;
}): Promise<Result> {
  try {
    if (!input.email.trim() || !input.password) {
      return { ok: false, error: "メールアドレスとパスワードは必須です" };
    }
    if (input.password.length < 8) {
      return { ok: false, error: "パスワードは8文字以上にしてください" };
    }
    const user = await createUser({
      email: input.email.trim(),
      name: input.name.trim() || input.email.trim(),
      password: input.password,
      businessName: input.businessName,
    });
    setSessionCookie(user.id);
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

export async function loginAction(input: {
  email: string;
  password: string;
}): Promise<Result> {
  try {
    const user = await findUserByEmail(input.email.trim());
    if (!user || !verifyPassword(input.password, user.passwordHash)) {
      return { ok: false, error: "メールアドレスまたはパスワードが正しくありません" };
    }
    setSessionCookie(user.id);
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

export async function logoutAction(): Promise<void> {
  clearSessionCookie();
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

// ---- Fixed assets ----
export async function saveFixedAssetAction(
  input: Omit<FixedAsset, "id" | "userId" | "createdAt">,
  id?: string,
): Promise<Result> {
  try {
    if (id) await updateFixedAsset(id, input);
    else await createFixedAsset(input);
    revalidatePath("/assets");
    revalidatePath("/reports/blue-return");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}

export async function deleteFixedAssetAction(id: string): Promise<Result> {
  try {
    await deleteFixedAsset(id);
    revalidatePath("/assets");
    return { ok: true };
  } catch (e) {
    return fail(e);
  }
}
