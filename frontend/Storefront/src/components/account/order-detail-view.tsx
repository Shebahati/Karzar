"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo } from "react";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { OrderTimeline } from "@/components/orders/order-timeline";
import { useOrderTracking } from "@/features/orders/queries";
import { useProductsByIds } from "@/features/catalog/queries";
import { formatNumber, formatToman } from "@/lib/utils";

export function OrderDetailView({ trackingCode }: { trackingCode: string }) {
  const { data, isPending, isError, refetch } = useOrderTracking(trackingCode);
  const productIds = useMemo(
    () => (data?.items ?? []).map((item) => item.product_id),
    [data?.items],
  );
  const productsQuery = useProductsByIds(productIds);
  const productsById = useMemo(() => {
    const map = new Map<number, { name: string; thumbnail: string | null; base_price: string | null }>();
    for (const p of productsQuery.data ?? []) {
      map.set(p.id, { name: p.name, thumbnail: p.thumbnail, base_price: p.base_price });
    }
    return map;
  }, [productsQuery.data]);

  return (
    <Container className="py-8 lg:py-12">
      <Link
        href={`/account/orders?mode=${data?.mode === "inquiry" ? "inquiry" : "purchase"}`}
        className="text-sm font-medium text-primary"
      >
        ← بازگشت به سفارش‌ها
      </Link>

      <h1 className="mt-4 text-2xl font-bold text-foreground">جزئیات سفارش</h1>

      {isPending && (
        <div className="mt-8 space-y-3">
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-40 w-full rounded-xl" />
        </div>
      )}

      {isError && (
        <div className="mt-8 rounded-xl bg-card p-8 text-center shadow-soft">
          <p className="text-sm text-destructive">سفارش یافت نشد یا بارگذاری ناموفق بود.</p>
          <Button className="mt-4" onClick={() => void refetch()}>
            تلاش مجدد
          </Button>
        </div>
      )}

      {data && (
        <div className="mt-8 space-y-6">
          <div className="rounded-xl bg-card p-6 shadow-soft">
            <p className="text-sm text-muted-foreground">کد پیگیری</p>
            <p className="mt-1 text-lg font-medium tnum" dir="ltr">
              {data.tracking_code}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-md bg-accent px-3 py-1 text-xs font-medium text-accent-foreground">
                {data.status_label}
              </span>
              <span className="rounded-md bg-secondary px-3 py-1 text-xs font-medium">
                {data.mode === "inquiry" ? "استعلام" : "خرید"}
              </span>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              {new Date(data.created_at).toLocaleDateString("fa-IR")}
            </p>

            {data.items?.length ? (
              <ul className="mt-4 space-y-3 border-t border-border pt-4">
                {data.items.map((item) => {
                  const product = productsById.get(item.product_id);
                  const name = product?.name ?? `کالای #${formatNumber(item.product_id)}`;
                  const thumb = product?.thumbnail;
                  return (
                    <li
                      key={`${item.product_id}-${item.quantity}`}
                      className="flex items-center gap-3 text-sm"
                    >
                      <Link
                        href={`/product/${item.product_id}`}
                        className="relative h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-secondary"
                      >
                        {thumb ? (
                          <Image
                            src={thumb}
                            alt={name}
                            fill
                            sizes="56px"
                            className="object-contain p-1"
                          />
                        ) : (
                          <span className="grid h-full place-items-center text-[10px] text-muted-foreground">
                            بدون تصویر
                          </span>
                        )}
                      </Link>
                      <div className="min-w-0 flex-1">
                        <Link
                          href={`/product/${item.product_id}`}
                          className="line-clamp-2 font-medium text-foreground hover:text-primary"
                        >
                          {name}
                        </Link>
                        {item.unit_price && (
                          <p className="mt-0.5 text-xs text-muted-foreground tnum">
                            {formatToman(item.unit_price)}
                          </p>
                        )}
                      </div>
                      <span className="shrink-0 text-muted-foreground tnum">
                        ×{formatNumber(item.quantity)}
                      </span>
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </div>

          {data.timeline?.length ? (
            <div className="rounded-xl bg-card p-6 shadow-soft">
              <h2 className="mb-1 font-medium text-foreground">
                وضعیت سفارش
                {data.timeline_estimated ? (
                  <span className="ms-2 text-xs font-normal text-muted-foreground">(تخمینی)</span>
                ) : null}
              </h2>
              <OrderTimeline
                events={data.timeline}
                estimated={Boolean(data.timeline_estimated)}
              />
            </div>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <Link href="/catalog">
              <Button variant="outline">ادامه خرید</Button>
            </Link>
            <Link href="/contact">
              <Button variant="ghost">پشتیبانی</Button>
            </Link>
          </div>
        </div>
      )}
    </Container>
  );
}
