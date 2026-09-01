"use client";

import Link from "next/link";
import { Bag2 } from "react-iconly";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAbandonedCarts } from "@/features/abandoned-carts/queries";
import { formatToman, toPersianDigits } from "@/lib/utils";

export default function AbandonedCartsPage() {
  const { data, isPending, isError, error } = useAbandonedCarts({ limit: 50 });
  const carts = data?.data ?? [];

  return (
    <div className="admin-page mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h2 className="admin-page-title">سبدهای رهاشده</h2>
        <p className="admin-page-subtitle">
          سبدهای خرید ثبت‌نام‌شده با فعالیت بیش از ۲۴ ساعت که هنوز به سفارش تبدیل نشده‌اند
          {data ? ` — ${data.meta.total_count.toLocaleString("fa-IR")} مورد` : ""}
        </p>
      </div>

      <Card className="admin-card">
        <CardContent className="p-0">
          {isPending ? (
            <div className="flex flex-col gap-3 p-6">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : isError ? (
            <p className="p-6 text-sm text-destructive">{(error as Error).message}</p>
          ) : carts.length === 0 ? (
            <p className="p-8 text-center text-sm text-muted-foreground">سبد رهاشده‌ای یافت نشد.</p>
          ) : (
            <ul className="divide-y divide-border">
              {carts.map((cart) => (
                <li key={cart.cart_id} className="flex flex-wrap items-center justify-between gap-4 p-5">
                  <div className="min-w-0">
                    <p className="font-bold text-foreground">{cart.customer_name}</p>
                    <p className="text-sm text-muted-foreground" dir="ltr">
                      {cart.customer_phone ?? "—"}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {toPersianDigits(cart.item_count)} قلم — آخرین فعالیت{" "}
                      {new Date(cart.last_activity_at).toLocaleString("fa-IR")}
                    </p>
                  </div>
                  <div className="text-end">
                    <p className="text-sm font-bold text-primary">{formatToman(Number(cart.cart_value))}</p>
                    {cart.user_id ? (
                      <Link href={`/customers/${cart.user_id}`} className="text-xs text-muted-foreground hover:text-primary">
                        مشاهده مشتری
                      </Link>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Bag2 size="small" set="light" />
        فقط کاربران ثبت‌نام‌شده — بدون ردیابی مهمان
      </div>
    </div>
  );
}
