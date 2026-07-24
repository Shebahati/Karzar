"use client";

import { Document, Download } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatToman, toPersianDigits } from "@/lib/utils";
import type { OrderDetail } from "@/types/order";

interface InvoiceCardProps {
  order: OrderDetail;
}

export function InvoiceCard({ order }: InvoiceCardProps) {
  const invoice = order.invoice;
  if (!invoice) return null;

  return (
    <Card className="border-primary/20 bg-gradient-to-br from-accent/40 to-card">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10">
            <Document set="bulk" size={22} primaryColor="#C22026" />
          </span>
          <div>
            <CardTitle className="text-base">پیش‌فاکتور / فاکتور</CardTitle>
            <p className="text-xs text-muted-foreground tnum">{toPersianDigits(invoice.invoice_number)}</p>
          </div>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => toast.success("دانلود PDF — پس از اتصال backend فعال می‌شود.")}
        >
          <Download set="light" size={16} />
          دانلود PDF
        </Button>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="grid gap-2 sm:grid-cols-2">
          <p>
            <span className="text-muted-foreground">تاریخ صدور: </span>
            {new Date(invoice.issued_at).toLocaleDateString("fa-IR")}
          </p>
          {invoice.valid_until && (
            <p>
              <span className="text-muted-foreground">اعتبار تا: </span>
              {new Date(invoice.valid_until).toLocaleDateString("fa-IR")}
            </p>
          )}
        </div>
        <p className="text-lg font-bold text-primary tnum">{formatToman(invoice.total)}</p>
        {invoice.note && (
          <p className="rounded-lg bg-muted/60 p-3 text-xs leading-6 text-muted-foreground">{invoice.note}</p>
        )}
        <ul className="divide-y divide-border rounded-lg border border-border">
          {order.items.map((item) => (
            <li key={item.product_id} className="flex justify-between gap-3 px-3 py-2 text-xs">
              <span>{item.product_name}</span>
              <span className="shrink-0 tnum">
                {formatToman(item.line_total)}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
