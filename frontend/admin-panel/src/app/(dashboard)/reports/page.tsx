"use client";

import Link from "next/link";
import { Activity, Bag2, Buy, Chart, Danger, Wallet } from "react-iconly";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useOrders } from "@/features/orders/queries";
import { useProductStatistics, useProducts } from "@/features/catalog/queries";
import { formatNumber, formatToman } from "@/lib/utils";
import type { IconlyIcon } from "@/components/layout/nav.config";

interface ReportStatProps {
  label: string;
  value: string;
  icon: IconlyIcon;
  loading?: boolean;
  hint?: string;
}

function ReportStat({ label, value, icon: Icon, loading, hint }: ReportStatProps) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent">
          <Icon set="bulk" size={24} primaryColor="#C22026" />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{label}</p>
          {loading ? (
            <Skeleton className="mt-1 h-6 w-24" />
          ) : (
            <p className="truncate text-xl font-bold tnum">{value}</p>
          )}
          {hint ? <p className="mt-0.5 text-[11px] text-muted-foreground">{hint}</p> : null}
        </div>
      </CardContent>
    </Card>
  );
}

export default function ReportsPage() {
  const { data: stats, isPending: statsPending, isError: statsError } = useProductStatistics();
  const { data: ordersData, isPending: ordersPending } = useOrders({ limit: 200 });
  const { data: productsData, isPending: productsPending } = useProducts({
    limit: 50,
    // Prefer low/out samples for ops attention when listing product rows.
  });

  const orders = ordersData?.data ?? [];
  const products = productsData?.data ?? [];

  const purchases = orders.filter((o) => o.mode === "purchase");
  const inquiries = orders.filter((o) => o.mode === "inquiry");
  const paid = purchases.filter((o) =>
    ["paid", "processing", "shipped", "delivered"].includes(o.status),
  );
  const revenue = paid.reduce((sum, o) => sum + Number(o.estimated_total ?? 0), 0);
  const outOfStock = products.filter((p) => p.stock_status === "out_of_stock");

  const needsAction = orders.filter(
    (o) =>
      o.status === "inquiry_review" ||
      o.status === "paid" ||
      o.status === "processing" ||
      o.status === "shipped",
  );

  const ordersLoading = ordersPending;
  const catalogLoading = statsPending;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">گزارش‌ها</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          آمار کاتالوگ از سرور؛ صف سفارش‌ها از نمونهٔ عملیاتی اخیر
        </p>
      </div>

      <div
        role="status"
        className="rounded-xl border border-border/70 bg-card px-4 py-3 text-sm leading-7 text-muted-foreground shadow-sm"
      >
        بخش کاتالوگ از{" "}
        <span className="font-bold text-foreground">GET /products/statistics</span> تغذیه می‌شود.
        صف «نیازمند اقدام» هنوز از حداکثر ۲۰۰ سفارش اخیر محاسبه می‌شود تا وقتی{" "}
        <span className="font-bold text-foreground">/reports</span> اختصاصی در بک‌اند آماده شود.
      </div>

      <div>
        <h3 className="mb-3 text-sm font-bold text-foreground">کاتالوگ (آمار سرور)</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <ReportStat
            label="کل محصولات"
            value={statsError ? "—" : formatNumber(stats?.total_products ?? 0)}
            icon={Bag2 as IconlyIcon}
            loading={catalogLoading}
            hint={stats ? `${formatNumber(stats.active_products)} فعال` : undefined}
          />
          <ReportStat
            label="ارزش موجودی"
            value={statsError ? "—" : formatToman(stats?.total_stock_value ?? 0)}
            icon={Wallet as IconlyIcon}
            loading={catalogLoading}
          />
          <ReportStat
            label="جمع موجودی عددی"
            value={statsError ? "—" : formatNumber(Number(stats?.total_stock_quantity ?? 0))}
            icon={Chart as IconlyIcon}
            loading={catalogLoading}
          />
          <ReportStat
            label="دسته / برند"
            value={
              statsError
                ? "—"
                : `${formatNumber(stats?.categories ?? 0)} / ${formatNumber(stats?.brands ?? 0)}`
            }
            icon={Activity as IconlyIcon}
            loading={catalogLoading}
          />
        </div>
      </div>

      <div>
        <h3 className="mb-3 text-sm font-bold text-foreground">سفارش‌ها (نمونهٔ اخیر)</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <ReportStat
            label="کل سفارش‌ها (نمونه)"
            value={formatNumber(orders.length)}
            icon={Buy as IconlyIcon}
            loading={ordersLoading}
          />
          <ReportStat
            label="سفارش خرید"
            value={formatNumber(purchases.length)}
            icon={Chart as IconlyIcon}
            loading={ordersLoading}
          />
          <ReportStat
            label="استعلام قیمت"
            value={formatNumber(inquiries.length)}
            icon={Activity as IconlyIcon}
            loading={ordersLoading}
          />
          <ReportStat
            label="درآمد پرداخت‌شده (نمونه)"
            value={formatToman(revenue)}
            icon={Wallet as IconlyIcon}
            loading={ordersLoading}
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-base font-bold text-foreground">نیازمند اقدام ادمین</h3>
            <Badge variant="outline">{formatNumber(needsAction.length)} مورد</Badge>
          </div>
          {ordersLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : needsAction.length === 0 ? (
            <p className="text-sm text-muted-foreground">همه پرونده‌ها به‌روز هستند.</p>
          ) : (
            <ul className="divide-y divide-border">
              {needsAction.slice(0, 8).map((order) => (
                <li
                  key={order.id}
                  className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="text-sm font-bold tnum">{order.tracking_code}</p>
                    <p className="text-xs text-muted-foreground">
                      {order.customer_name} — {order.status_label}
                    </p>
                  </div>
                  <Button asChild variant="outline" size="sm">
                    <Link href={`/orders/${order.id}`}>اقدام</Link>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-6">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-warning/15">
              <Danger set="bulk" size={22} primaryColor="#B45309" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">کالاهای ناموجود (نمونه صفحه)</h3>
              <p className="mt-1 text-sm text-muted-foreground tnum">
                {productsPending ? "…" : `${formatNumber(outOfStock.length)} مورد در این صفحه`}
              </p>
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href="/catalog/products">مدیریت موجودی</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
