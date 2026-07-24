"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowRight } from "react-iconly";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { OrderStatusStepper } from "@/features/orders/components/order-status-stepper";
import { OrderActionPanel } from "@/features/orders/components/order-action-panel";
import { InvoiceCard } from "@/features/orders/components/invoice-card";
import { useEnrichedOrder } from "@/features/orders/use-enriched-order";
import { formatToman, toPersianDigits } from "@/lib/utils";

export default function OrderDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const { data: order, isPending, isEnriching } = useEnrichedOrder(id);

  if (isPending) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 px-1">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }

  if (!order) {
    return <p className="p-8 text-center text-sm">سفارش یافت نشد.</p>;
  }

  const backHref = order.mode === "inquiry" ? "/quotes" : "/orders";

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5 px-1 sm:gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button asChild variant="ghost" size="icon" className="mt-0.5 shrink-0">
            <Link href={backHref} aria-label="بازگشت">
              <ArrowRight set="light" size={22} />
            </Link>
          </Button>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-bold text-foreground tnum sm:text-2xl">
                {toPersianDigits(order.tracking_code)}
              </h2>
              <Badge variant="outline">{order.mode === "inquiry" ? "استعلام" : "خرید"}</Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{order.status_label}</p>
          </div>
        </div>
      </div>

      <OrderStatusStepper order={order} />

      <div className="grid gap-5 lg:grid-cols-[1fr_320px] lg:gap-6">
        <div className="flex flex-col gap-5 sm:gap-6">
          {order.invoice && <InvoiceCard order={order} />}

          <div className="grid gap-5 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">مشتری</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  <span className="text-muted-foreground">نام: </span>
                  {order.customer_name}
                </p>
                <p className="tnum">
                  <span className="text-muted-foreground">موبایل: </span>
                  {toPersianDigits(order.customer_phone)}
                </p>
                {order.shipping_address && (
                  <p>
                    <span className="text-muted-foreground">آدرس: </span>
                    {order.shipping_address}
                  </p>
                )}
                {order.note && (
                  <p>
                    <span className="text-muted-foreground">یادداشت: </span>
                    {order.note}
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">مالی</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  <span className="text-muted-foreground">مبلغ: </span>
                  <span className="font-bold tnum">{formatToman(order.estimated_total)}</span>
                </p>
                <p>
                  <span className="text-muted-foreground">وضعیت پرداخت: </span>
                  {order.payment_status ?? "—"}
                </p>
                <p>
                  <span className="text-muted-foreground">تاریخ ثبت: </span>
                  {new Date(order.created_at).toLocaleString("fa-IR")}
                </p>
                {order.postal_tracking_code && (
                  <p className="tnum">
                    <span className="text-muted-foreground">رهگیری پست: </span>
                    {toPersianDigits(order.postal_tracking_code)}
                  </p>
                )}
                {order.delivery_eta && (
                  <p>
                    <span className="text-muted-foreground">تحویل تقریبی: </span>
                    {new Date(order.delivery_eta).toLocaleString("fa-IR")}
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                اقلام {isEnriching && <span className="text-xs text-muted-foreground">(بارگذاری…)</span>}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-border">
                {order.items.map((item) => (
                  <li
                    key={`${item.product_id}-${item.sku}`}
                    className="flex flex-col gap-1 py-3 text-sm sm:flex-row sm:justify-between"
                  >
                    <div>
                      <p className="font-bold">{item.product_name}</p>
                      <p className="text-xs text-muted-foreground tnum">{item.sku}</p>
                    </div>
                    <div className="text-start sm:text-end">
                      <p className="tnum">
                        {toPersianDigits(item.quantity)} × {formatToman(item.unit_price)}
                      </p>
                      <p className="font-bold tnum">{formatToman(item.line_total)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {order.timeline && order.timeline.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">تاریخچه</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-3">
                  {order.timeline.map((event, idx) => (
                    <li key={`${event.status}-${idx}`} className="border-s-2 border-primary/30 ps-4">
                      <p className="text-sm font-bold">{event.status_label}</p>
                      <p className="text-xs text-muted-foreground">{event.description}</p>
                      <p className="mt-0.5 text-[10px] text-muted-foreground/80 tnum">
                        {new Date(event.occurred_at).toLocaleString("fa-IR")}
                      </p>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="lg:sticky lg:top-24 lg:self-start">
          <OrderActionPanel order={order} />
        </div>
      </div>
    </div>
  );
}
