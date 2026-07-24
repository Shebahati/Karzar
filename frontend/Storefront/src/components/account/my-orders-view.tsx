"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Bag, Home } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMyOrders } from "@/features/orders/queries";
import { isLoggedIn } from "@/lib/api-client";
import { cn, formatNumber } from "@/lib/utils";

type OrdersTab = "purchase" | "inquiry";

function resolveTab(raw: string | null): OrdersTab {
  return raw === "inquiry" ? "inquiry" : "purchase";
}

export function MyOrdersView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = resolveTab(searchParams.get("mode"));
  const { data, isPending, isError } = useMyOrders({ limit: 50 });
  const authed = isLoggedIn();

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login?next=/account/orders");
    }
  }, [router]);

  // Normalize missing/invalid mode to purchase so the default is honest.
  useEffect(() => {
    const raw = searchParams.get("mode");
    if (raw !== "purchase" && raw !== "inquiry") {
      const next = new URLSearchParams(searchParams.toString());
      next.set("mode", "purchase");
      router.replace(`/account/orders?${next.toString()}`);
    }
  }, [router, searchParams]);

  if (!authed) {
    return (
      <Container className="py-16">
        <p className="text-center text-sm text-muted-foreground">در حال هدایت به ورود…</p>
      </Container>
    );
  }

  const rows = data?.data.filter((o) => o.mode === tab) ?? [];

  function setTab(next: OrdersTab) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("mode", next);
    router.replace(`/account/orders?${params.toString()}`);
  }

  return (
    <Container className="py-8 lg:py-12">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link href="/account" className="text-sm text-primary">
            ← حساب کاربری
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-foreground">
            {tab === "inquiry" ? "استعلام‌های من" : "سفارش‌های من"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">پیگیری وضعیت ثبت‌شده‌ها</p>
        </div>
      </div>

      <div
        role="tablist"
        aria-label="نوع سفارش"
        className="mt-6 flex gap-2 rounded-xl bg-secondary p-1"
      >
        {(
          [
            { id: "purchase" as const, label: "خریدها" },
            { id: "inquiry" as const, label: "استعلام‌ها" },
          ] as const
        ).map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            onClick={() => setTab(item.id)}
            className={cn(
              "flex-1 rounded-lg px-4 py-2.5 text-sm font-bold transition-colors",
              tab === item.id
                ? "bg-card text-foreground shadow-soft"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="mt-8">
        {isPending && (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full rounded-xl" />
            <Skeleton className="h-20 w-full rounded-xl" />
          </div>
        )}

        {isError && (
          <div className="rounded-xl bg-card p-8 text-center shadow-soft">
            <p className="text-sm text-destructive">بارگذاری سفارش‌ها با خطا مواجه شد.</p>
          </div>
        )}

        {!isPending && !isError && rows.length === 0 && (
          <div className="grid place-items-center rounded-xl bg-card py-16 text-center shadow-soft">
            <span className="grid h-16 w-16 place-items-center rounded-xl bg-accent text-primary">
              <Bag set="bold" />
            </span>
            <p className="mt-4 font-medium text-foreground">
              {tab === "inquiry" ? "استعلامی ثبت نشده است" : "سفارشی ثبت نشده است"}
            </p>
            <Link href="/catalog" className="mt-6">
              <Button>مشاهده محصولات</Button>
            </Link>
          </div>
        )}

        {rows.length > 0 && (
          <ul className="divide-y divide-border rounded-xl bg-card shadow-soft">
            {rows.map((order) => (
              <li key={order.id} className="flex flex-wrap items-center justify-between gap-4 p-5">
                <div>
                  <p className="font-medium text-foreground tnum" dir="ltr">
                    {order.tracking_code}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {new Date(order.created_at).toLocaleDateString("fa-IR")}
                  </p>
                </div>
                <div className="text-end">
                  <div className="flex flex-wrap justify-end gap-1.5">
                    <span className="rounded-md bg-accent px-3 py-1 text-xs font-medium text-accent-foreground">
                      {order.status_label}
                    </span>
                    {order.mode === "purchase" && (
                      <span
                        className={
                          order.status === "pending_payment"
                            ? "rounded-md bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive"
                            : "rounded-md bg-success/10 px-2.5 py-1 text-xs font-medium text-success"
                        }
                      >
                        {order.status === "pending_payment" ? "پرداخت‌نشده" : "پرداخت‌شده"}
                      </span>
                    )}
                  </div>
                  {order.estimated_total && (
                    <p className="mt-1 text-sm text-muted-foreground tnum">
                      {formatNumber(order.estimated_total)} تومان
                    </p>
                  )}
                </div>
                <Link
                  href={`/account/orders/${encodeURIComponent(order.tracking_code)}`}
                  className="w-full sm:w-auto"
                >
                  <Button variant="soft" size="sm" className="w-full sm:w-auto">
                    جزئیات
                  </Button>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-8">
        <Link href="/">
          <Button variant="ghost" className="gap-2">
            <Home set="light" />
            بازگشت به خانه
          </Button>
        </Link>
      </div>
    </Container>
  );
}
