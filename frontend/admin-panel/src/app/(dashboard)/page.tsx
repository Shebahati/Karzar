"use client";

import Link from "next/link";
import { Bag2, Buy, Category, Danger, Plus, Ticket } from "react-iconly";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { StatValue } from "@/components/ui/stat-value";
import { SystemStatusStrip } from "@/components/system-status-strip";
import { useCategories, useProducts, useProductStatistics } from "@/features/catalog/queries";
import { useWebsitePaidSales } from "@/features/hesabfa/queries";
import { useOrders } from "@/features/orders/queries";
import { formatNumber, formatToman, toPersianDigits } from "@/lib/utils";
import type { IconlyIcon } from "@/components/layout/nav.config";

interface StatCardProps {
  label: string;
  value: string;
  icon: IconlyIcon;
  tone?: "primary" | "success" | "warning" | "neutral";
  loading?: boolean;
}

const TONE_STYLES: Record<NonNullable<StatCardProps["tone"]>, { bg: string; color: string }> = {
  primary: { bg: "bg-accent", color: "#D02327" },
  success: { bg: "bg-success/12", color: "#2E9E5B" },
  warning: { bg: "bg-warning/15", color: "#B45309" },
  neutral: { bg: "bg-secondary", color: "#4F4F4F" },
};

function StatCard({ label, value, icon: Icon, tone = "primary", loading }: StatCardProps) {
  const style = TONE_STYLES[tone];
  return (
    <Card className="hover:shadow-elevated">
      <CardContent className="flex items-start gap-3 p-5 sm:gap-4">
        <div
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl sm:h-14 sm:w-14 ${style.bg}`}
        >
          <Icon set="bulk" size={28} primaryColor={style.color} />
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-1 overflow-visible">
          <span className="text-sm leading-snug text-muted-foreground">{label}</span>
          {loading ? (
            <Skeleton className="h-6 w-20" />
          ) : (
            <StatValue value={value} />
          )}
        </div>
      </CardContent>
    </Card>
  );
}

interface QueueItem {
  key: string;
  href: string;
  title: string;
  subtitle: string;
  badgeLabel: string;
  badgeVariant: "danger" | "warning" | "outline";
}

function ActionQueueList({ items, loading, emptyLabel }: { items: QueueItem[]; loading: boolean; emptyLabel: string }) {
  if (loading) {
    return (
      <div className="flex flex-col gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    );
  }
  if (items.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">{emptyLabel}</p>;
  }
  return (
    <ul className="flex flex-col gap-2">
      {items.map((item) => (
        <li key={item.key}>
          <Link
            href={item.href}
            className="flex items-center justify-between gap-3 rounded-lg bg-muted/60 px-4 py-3 transition-colors hover:bg-muted"
          >
            <div className="flex min-w-0 flex-col">
              <span className="truncate text-sm font-bold text-foreground">{item.title}</span>
              <span className="text-xs text-muted-foreground">{item.subtitle}</span>
            </div>
            <Badge variant={item.badgeVariant}>{item.badgeLabel}</Badge>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export default function DashboardPage() {
  const { data: stats, isPending: statsPending } = useProductStatistics();
  const { data: productsData, isPending: productsPending } = useProducts({ limit: 100 });
  const { data: categories } = useCategories();
  const { data: websiteSalesSummary, isPending: salesPending } = useWebsitePaidSales();

  const products = productsData?.data ?? [];
  const totalProducts = stats?.total_products ?? productsData?.meta.total_count ?? 0;
  const availableProducts =
    stats?.available_products ??
    Number(stats?.total_stock_quantity ?? products.filter((p) => p.availability).length);
  const outOfStock = products.filter((p) => p.stock_status === "out_of_stock");
  const lowStock = products.filter((p) => p.stock_status === "low_stock");
  const categoryCount =
    stats?.categories ??
    (categories ?? []).reduce((sum, c) => sum + 1 + c.subcategories.length, 0);

  const websiteSales =
    websiteSalesSummary?.website_paid_total_toman != null
      ? Number(websiteSalesSummary.website_paid_total_toman)
      : null;

  const { data: openPurchaseOrders, isPending: openPurchasePending } = useOrders({
    mode: "purchase",
    open: true,
    limit: 6,
  });
  const { data: openInquiries, isPending: inquiriesPending } = useOrders({
    mode: "inquiry",
    open: true,
    limit: 6,
  });

  const paidQueue: QueueItem[] = (openPurchaseOrders?.data ?? []).map((order) => ({
    key: `order-${order.id}`,
    href: `/orders/${order.id}`,
    title: toPersianDigits(order.tracking_code),
    subtitle: `${order.customer_name} — ${order.status_label}`,
    badgeLabel: "پردازش سفارش",
    badgeVariant: "warning" as const,
  }));

  const inquiryQueue: QueueItem[] = (openInquiries?.data ?? []).map((order) => ({
    key: `inquiry-${order.id}`,
    href: `/orders/${order.id}`,
    title: toPersianDigits(order.tracking_code),
    subtitle: `${order.customer_name} — استعلام باز، نیاز به پیش‌فاکتور`,
    badgeLabel: "صدور پیش‌فاکتور",
    badgeVariant: "outline" as const,
  }));

  const stockQueue: QueueItem[] = [
    ...outOfStock.map((product) => ({
      key: `oos-${product.id}`,
      href: `/catalog/products/${product.id}/edit`,
      title: product.name,
      subtitle: product.sku,
      badgeLabel: "ناموجود",
      badgeVariant: "danger" as const,
    })),
    ...lowStock.map((product) => ({
      key: `low-${product.id}`,
      href: `/catalog/products/${product.id}/edit`,
      title: product.name,
      subtitle: product.sku,
      badgeLabel: "موجودی کم",
      badgeVariant: "warning" as const,
    })),
  ];

  const totalQueueCount = paidQueue.length + inquiryQueue.length + stockQueue.length;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="admin-page-title">امروز — صف اقدامات</h2>
          <p className="admin-page-subtitle">
            نمای عملیاتی فروشگاه ابزارآلات صنعتی کارزار — {formatNumber(totalQueueCount)} مورد نیازمند
            بررسی
          </p>
        </div>
        <Button asChild>
          <Link href="/catalog/products/new">
            <Plus set="bold" size={20} primaryColor="#FFFFFF" />
            افزودن محصول جدید
          </Link>
        </Button>
      </div>

      <SystemStatusStrip />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="فروش وبسایت (پرداخت‌شده)"
          value={websiteSales !== null ? formatToman(websiteSales) : "—"}
          icon={Buy as IconlyIcon}
          tone="success"
          loading={salesPending}
        />
        <StatCard
          label="کل محصولات"
          value={formatNumber(totalProducts)}
          icon={Bag2 as IconlyIcon}
          tone="primary"
          loading={statsPending && productsPending}
        />
        <StatCard
          label="محصولات موجود"
          value={formatNumber(availableProducts)}
          icon={Bag2 as IconlyIcon}
          tone="success"
          loading={statsPending}
        />
        <StatCard
          label="دسته‌بندی‌ها"
          value={formatNumber(categoryCount)}
          icon={Category as IconlyIcon}
          tone="neutral"
          loading={statsPending}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard
          label="کالاهای نیازمند توجه"
          value={formatNumber(outOfStock.length + lowStock.length)}
          icon={Danger as IconlyIcon}
          tone="warning"
          loading={productsPending}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card>
          <CardContent className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Buy set="bulk" size={20} primaryColor="#D02327" />
                <h3 className="text-sm font-bold text-foreground">سفارش‌های در انتظار پردازش</h3>
              </div>
              <Button asChild variant="ghost" size="sm">
                <Link href="/orders">مشاهده همه</Link>
              </Button>
            </div>
            <ActionQueueList items={paidQueue} loading={openPurchasePending} emptyLabel="سفارش پرداخت‌شده‌ای در صف نیست." />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Ticket set="bulk" size={20} primaryColor="#D02327" />
                <h3 className="text-sm font-bold text-foreground">استعلام‌های باز</h3>
              </div>
              <Button asChild variant="ghost" size="sm">
                <Link href="/quotes">مشاهده همه</Link>
              </Button>
            </div>
            <ActionQueueList
              items={inquiryQueue}
              loading={inquiriesPending}
              emptyLabel="استعلام بازی برای بررسی نیست."
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="mb-5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Danger set="bulk" size={22} primaryColor="#D02327" />
              <h3 className="text-base font-bold text-foreground">کالاهای نیازمند توجه در انبار</h3>
            </div>
            <Button asChild variant="ghost" size="sm">
              <Link href="/catalog/products">مشاهده همه</Link>
            </Button>
          </div>
          <ActionQueueList
            items={stockQueue}
            loading={productsPending}
            emptyLabel="همه‌ی کالاها موجود هستند. وضعیت انبار سالم است."
          />
        </CardContent>
      </Card>
    </div>
  );
}
