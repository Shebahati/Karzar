"use client";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Wallet } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMyOrders } from "@/features/orders/queries";
import { isLoggedIn } from "@/lib/api-client";
import { cn, formatToman, toPersianDigits } from "@/lib/utils";
import type { OrderStatus, OrderSummary } from "@/types/order";

type PaymentTone = "paid" | "pending" | "cancelled" | "other";

function paymentMeta(order: OrderSummary): {
  label: string;
  tone: PaymentTone;
} {
  const status = order.status;
  if (order.mode === "inquiry") {
    if (status === "inquiry_quoted") {
      return { label: "پیش‌فاکتور صادر شده", tone: "other" };
    }
    if (status === "inquiry_closed") {
      return { label: "بسته شده", tone: "cancelled" };
    }
    return { label: "در انتظار بررسی", tone: "pending" };
  }

  const paidLike: OrderStatus[] = ["paid", "processing", "shipped", "delivered"];
  if (paidLike.includes(status)) {
    return { label: "پرداخت‌شده", tone: "paid" };
  }
  if (status === "pending_payment") {
    return { label: "در انتظار پرداخت", tone: "pending" };
  }
  if (status === "cancelled") {
    return { label: "لغو شده", tone: "cancelled" };
  }
  return { label: order.status_label || status, tone: "other" };
}

const TONE_CLASS: Record<PaymentTone, string> = {
  paid: "bg-emerald-50 text-emerald-800",
  pending: "bg-amber-50 text-amber-900",
  cancelled: "bg-secondary text-steel",
  other: "bg-accent text-primary",
};

export function AccountPaymentsView() {
  const router = useRouter();
  const { data, isPending, isError, refetch } = useMyOrders({ limit: 50 });

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login?next=/account/payments");
  }, [router]);

  const purchases = useMemo(
    () => (data?.data ?? []).filter((o) => o.mode === "purchase"),
    [data],
  );

  const stats = useMemo(() => {
    let paid = 0;
    let pending = 0;
    let cancelled = 0;
    for (const o of purchases) {
      const { tone } = paymentMeta(o);
      if (tone === "paid") paid += 1;
      else if (tone === "pending") pending += 1;
      else if (tone === "cancelled") cancelled += 1;
    }
    return { paid, pending, cancelled };
  }, [purchases]);

  if (!isLoggedIn()) {
    return (
      <Container className="py-16">
        <p className="text-center text-sm text-steel">در حال هدایت به ورود…</p>
      </Container>
    );
  }

  return (
    <Container className="py-8 lg:py-12">
      <Link href="/account" className="text-sm text-primary">
        ← حساب کاربری
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-foreground">پرداخت‌ها</h1>
      <p className="mt-1 text-sm text-steel">
        وضعیت پرداخت سفارش‌های خرید بر اساس آخرین وضعیت ثبت‌شده
      </p>

      <div className="mt-6 grid grid-cols-3 gap-3">
        {(
          [
            { label: "پرداخت‌شده", value: stats.paid },
            { label: "در انتظار", value: stats.pending },
            { label: "لغو شده", value: stats.cancelled },
          ] as const
        ).map((item) => (
          <div
            key={item.label}
            className="rounded-2xl border border-border/40 bg-card p-4 text-center shadow-soft"
          >
            <p className="text-2xl font-bold text-foreground tnum">
              {toPersianDigits(item.value)}
            </p>
            <p className="mt-1 text-[11px] text-steel">{item.label}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 space-y-3">
        {isPending &&
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-2xl" />
          ))}

        {isError && (
          <div className="rounded-2xl bg-card p-8 text-center shadow-soft">
            <p className="font-medium text-foreground">بارگذاری ناموفق بود</p>
            <Button className="mt-4" onClick={() => void refetch()}>
              تلاش مجدد
            </Button>
          </div>
        )}

        {!isPending && !isError && purchases.length === 0 && (
          <div className="grid place-items-center rounded-2xl bg-card py-16 text-center shadow-soft">
            <span className="grid h-14 w-14 place-items-center rounded-2xl bg-secondary text-steel">
              <Wallet set="bold" />
            </span>
            <p className="mt-4 font-bold text-foreground">پرداختی ثبت نشده</p>
            <p className="mt-1 text-sm text-steel">سفارش‌های خرید در اینجا نمایش داده می‌شوند.</p>
          </div>
        )}

        {purchases.map((order) => {
          const meta = paymentMeta(order);
          return (
            <Link
              key={order.id}
              href={`/account/orders/${order.tracking_code}`}
              className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/40 bg-card p-5 shadow-soft transition-shadow hover:shadow-card"
            >
              <div>
                <p className="font-bold text-foreground tnum">
                  {toPersianDigits(order.tracking_code)}
                </p>
                <p className="mt-0.5 text-xs text-steel">
                  {toPersianDigits(order.created_at.slice(0, 10))}
                  {order.estimated_total
                    ? ` · ${formatToman(order.estimated_total)}`
                    : ""}
                </p>
              </div>
              <span
                className={cn(
                  "rounded-lg px-3 py-1.5 text-xs font-bold",
                  TONE_CLASS[meta.tone],
                )}
              >
                {meta.label}
              </span>
            </Link>
          );
        })}
      </div>
    </Container>
  );
}
