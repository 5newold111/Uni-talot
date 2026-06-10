import { notFound } from "next/navigation";
import { PageHeader } from "@/components/ui";
import { InvoiceForm } from "@/components/InvoiceForm";
import { getInvoice, listPartners } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function EditInvoicePage({
  params,
}: {
  params: { id: string };
}) {
  const [inv, partners] = await Promise.all([getInvoice(params.id), listPartners()]);
  if (!inv) notFound();
  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title={`請求書 ${inv.number}`} description="内容を編集します" />
      <InvoiceForm partners={partners} defaultNumber={inv.number} initial={inv} />
    </div>
  );
}
