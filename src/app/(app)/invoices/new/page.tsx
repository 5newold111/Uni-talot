import { PageHeader } from "@/components/ui";
import { InvoiceForm } from "@/components/InvoiceForm";
import { listPartners, nextInvoiceNumber } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function NewInvoicePage() {
  const [partners, number] = await Promise.all([listPartners(), nextInvoiceNumber()]);
  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title="請求書を作成" description="適格請求書（インボイス）の要件に沿って税率区分ごとに集計します" />
      <InvoiceForm partners={partners} defaultNumber={number} />
    </div>
  );
}
