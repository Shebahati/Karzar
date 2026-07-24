"use client";

import Link from "next/link";
import { Activity, Buy, Chart, Wallet } from "react-iconly";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useOrders } from "@/features/orders/queries";
import { useProducts } from "@/features/catalog/queries";
import { formatNumber, formatToman } from "@/lib/utils";
import type { IconlyIcon } from "@/components/layout/nav.config";

interface ReportStatProps {
  label: string;
  value: string;
  icon: IconlyIcon;
  loading?: boolean;
}

function ReportStat({ label, value, icon: Icon, loading }: ReportStatProps) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent">
          <Icon set="bulk" size={24} primaryColor="#C22026" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          {loading ? <Skeleton className="mt-1 h-6 w-24" /> : <p className="text-xl font-bold tnum">{value}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

export default function ReportsPage() {
  const { data: ordersData, isPending: ordersPending } = useOrders({ limit: 200 });
  const { data: productsData, isPending: productsPending } = useProducts({ limit: 200 });

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

  const loading = ordersPending || productsPending;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">گزارش‌ها</h2>
        <p className="mt-1 text-sm text-muted-foreground">نمای عملیاتی فروشگاه</p>
      </div>

      <div
        role="status"
        className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
      >
        این صفحه بر اساس حداکثر ۲۰۰ ردیف اخیر سفارش و محصول محاسبه می‌شود — گزارش رسمی سروری
        نیست.
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <ReportStat label="کل سفارش‌ها" value={formatNumber(orders.length)} icon={Buy as IconlyIcon} loading={loading} />
        <ReportStat label="سفارش خرید" value={formatNumber(purchases.length)} icon={Chart as IconlyIcon} loading={loading} />
        <ReportStat label="استعلام قیمت" value={formatNumber(inquiries.length)} icon={Activity as IconlyIcon} loading={loading} />
        <ReportStat label="درآمد پرداخت‌شده" value={formatToman(revenue)} icon={Wallet as IconlyIcon} loading={loading} />
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-base font-bold text-foreground">نیازمند اقدام ادمین</h3>
            <Badge variant="outline">{formatNumber(needsAction.length)} مورد</Badge>
          </div>
          {loading ? (
            <Skeleton className="h-24 w-full" />
          ) : needsAction.length === 0 ? (
            <p className="text-sm text-muted-foreground">همه پرونده‌ها به‌روز هستند.</p>
          ) : (
            <ul className="divide-y divide-border">
              {needsAction.slice(0, 8).map((order) => (
                <li key={order.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-bold tnum">{order.tracking_code}</p>
                    <p className="text-xs text-muted-foreground">{order.customer_name} — {order.status_label}</p>
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
        <CardContent className="p-6">
          <h3 className="text-base font-bold text-foreground">کالاهای ناموجود</h3>
          <p className="mt-1 text-sm text-muted-foreground tnum">{formatNumber(outOfStock.length)} محصول</p>
          <Button asChild variant="ghost" size="sm" className="mt-3">
            <Link href="/catalog/products">مدیریت موجودی</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
