"use client";

import Link from "next/link";
import { Buy, Document } from "react-iconly";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useOrders } from "@/features/orders/queries";
import { formatNumber, formatToman, toPersianDigits } from "@/lib/utils";

interface CustomerOrdersSectionProps {
  phone: string;
}

export function CustomerOrdersSection({ phone }: CustomerOrdersSectionProps) {
  const { data, isPending } = useOrders({ customer_phone: phone, limit: 100 });
  const orders = data?.data ?? [];
  const purchases = orders.filter((o) => o.mode === "purchase");
  const inquiries = orders.filter((o) => o.mode === "inquiry");

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
        <CardTitle className="text-base">سوابق سفارش و استعلام</CardTitle>
        <span className="text-xs text-muted-foreground tnum">
          {formatNumber(orders.length)} پرونده
        </span>
      </CardHeader>
      <CardContent className="space-y-6">
        {isPending ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : orders.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">هنوز سفارشی ثبت نشده است.</p>
        ) : (
          <>
            {purchases.length > 0 && (
              <OrderGroup title="سفارش‌های خرید" orders={purchases} icon="purchase" />
            )}
            {inquiries.length > 0 && (
              <OrderGroup title="استعلام‌های قیمت" orders={inquiries} icon="inquiry" />
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function OrderGroup({
  title,
  orders,
  icon,
}: {
  title: string;
  orders: Array<{
    id: number;
    tracking_code: string;
    status_label: string;
    estimated_total: string | null;
    created_at: string;
  }>;
  icon: "purchase" | "inquiry";
}) {
  return (
    <div>
      <div className="mb-3 flex items-center gap-2 text-sm font-bold text-foreground">
        {icon === "purchase" ? (
          <Buy set="bulk" size={18} primaryColor="#C22026" />
        ) : (
          <Document set="bulk" size={18} primaryColor="#C22026" />
        )}
        {title}
        <Badge variant="outline" className="tnum">
          {formatNumber(orders.length)}
        </Badge>
      </div>
      <ul className="divide-y divide-border rounded-xl border border-border">
        {orders.map((order) => (
          <li
            key={order.id}
            className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0">
              <p className="text-sm font-bold text-foreground tnum">
                {toPersianDigits(order.tracking_code)}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {new Date(order.created_at).toLocaleString("fa-IR")} — {order.status_label}
              </p>
              <p className="mt-1 text-sm font-bold tnum">{formatToman(order.estimated_total)}</p>
            </div>
            <Button asChild variant="outline" size="sm" className="shrink-0">
              <Link href={`/orders/${order.id}`}>مشاهده کامل</Link>
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
