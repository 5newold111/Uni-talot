import { redirect } from "next/navigation";
import { AuthForm } from "@/components/AuthForm";
import { getSessionUserId } from "@/lib/session";

export const dynamic = "force-dynamic";

export default function RegisterPage() {
  if (getSessionUserId()) redirect("/");
  return <AuthForm mode="register" />;
}
