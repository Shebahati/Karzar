"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Document, Download } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMyOrders } from "@/features/orders/queries";
import { orderService } from "@/services/orders";
import { downloadOrderPdf } from "@/lib/invoice-pdf";
import { isLoggedIn } from "@/lib/api-client";
import { formatNumber, formatToman, toPersianDigits } from "@/lib/utils";
import type { OrderSummary } from "@/types/order";

export function AccountInvoicesView() {
  const router = useRouter();
  const { data, isPending, isError, refetch } = useMyOrders({ limit: 50 });
  const [busyCode, setBusyCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login?next=/account/invoices");
  }, [router]);

  if (!isLoggedIn()) {
    return (
      <Container className="py-16">
        <p className="text-center text-sm text-steel">در حال هدایت به ورود…</p>
      </Container>
    );
  }

  const rows = data?.data ?? [];

  const handleDownload = async (order: OrderSummary) => {
    setError(null);
    setBusyCode(order.tracking_code);
    try {
      const tracking = await orderService.track(order.tracking_code);
      await downloadOrderPdf(
        {
          ...tracking,
          estimated_total: tracking.estimated_total ?? order.estimated_total,
        },
        order.mode === "inquiry" ? "proforma" : "invoice",
      );
    } catch {
      setError("دانلود فایل ناموفق بود. دوباره تلاش کنید.");
    } finally {
      setBusyCode(null);
    }
  };

  return (
    <Container className="py-8 lg:py-12">
      <Link href="/account" className="text-sm text-primary">
        ← حساب کاربری
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-foreground">فاکتورها و پیش‌فاکتورها</h1>
      <p className="mt-1 text-sm text-steel">
        دانلود فاکتور خرید یا پیش‌فاکتور استعلام به‌صورت PDF
      </p>

      {error && (
        <p className="mt-4 text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <div className="mt-6 space-y-3">
        {isPending &&
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-2xl" />
          ))}

        {isError && (
          <div className="rounded-2xl bg-card p-8 text-center shadow-soft">
            <p className="font-medium text-foreground">بارگذاری سفارش‌ها ناموفق بود</p>
            <Button className="mt-4" onClick={() => void refetch()}>
              تلاش مجدد
            </Button>
          </div>
        )}

        {!isPending && !isError && rows.length === 0 && (
          <div className="grid place-items-center rounded-2xl bg-card py-16 text-center shadow-soft">
            <span className="grid h-14 w-14 place-items-center rounded-2xl bg-secondary text-steel">
              <Document set="bold" />
            </span>
            <p className="mt-4 font-bold text-foreground">هنوز فاکتوری ندارید</p>
            <p className="mt-1 text-sm text-steel">پس از ثبت سفارش، فایل PDF اینجا ظاهر می‌شود.</p>
          </div>
        )}

        {rows.map((order) => {
          const kind = order.mode === "inquiry" ? "پیش‌فاکتور" : "فاکتور";
          const busy = busyCode === order.tracking_code;
          return (
            <article
              key={order.id}
              className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-border/40 bg-card p-5 shadow-soft"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-md bg-secondary px-2 py-0.5 text-[10px] font-bold text-steel">
                    {kind}
                  </span>
                  <span className="text-xs text-steel">{order.status_label}</span>
                </div>
                <p className="mt-1 font-bold text-foreground tnum">
                  {toPersianDigits(order.tracking_code)}
                </p>
                <p className="mt-0.5 text-xs text-steel">
                  {toPersianDigits(order.created_at.slice(0, 10))}
                  {order.estimated_total
                    ? ` · ${formatToman(order.estimated_total)}`
                    : ""}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    router.push(`/account/orders/${order.tracking_code}`)
                  }
                >
                  جزئیات
                </Button>
                <Button
                  size="sm"
                  className="gap-1"
                  disabled={busy}
                  onClick={() => void handleDownload(order)}
                >
                  <Download set="bold" size="small" />
                  {busy ? "در حال ساخت…" : `دانلود ${kind}`}
                </Button>
              </div>
            </article>
          );
        })}
      </div>

      {rows.length > 0 && (
        <p className="mt-4 text-xs text-steel">
          {formatNumber(rows.length)} مورد
        </p>
      )}
    </Container>
  );
}
