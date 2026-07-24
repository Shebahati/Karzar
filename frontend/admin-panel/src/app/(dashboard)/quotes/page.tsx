"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Document, Filter, Search } from "react-iconly";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useOrders } from "@/features/orders/queries";
import { ApiError } from "@/lib/api-client";
import { formatNumber, formatToman } from "@/lib/utils";
import type { OrderStatus } from "@/types/order";

const INQUIRY_STATUSES: OrderStatus[] = [
  "inquiry_review",
  "inquiry_quoted",
  "inquiry_closed",
];

const STATUS_LABELS: Record<OrderStatus, string> = {
  pending_payment: "در انتظار پرداخت",
  paid: "پرداخت شده",
  processing: "در حال پردازش",
  shipped: "ارسال شده",
  delivered: "تحویل شده",
  cancelled: "لغو شده",
  inquiry_review: "در حال بررسی استعلام",
  inquiry_quoted: "پیش‌فاکتور صادر شد",
  inquiry_closed: "پرونده بسته شد",
};

export default function QuotesPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string>("");

  const listParams = useMemo(
    () => ({
      limit: 50,
      search: search.trim() || undefined,
      status: (status || undefined) as OrderStatus | undefined,
      mode: "inquiry" as const,
    }),
    [search, status],
  );

  const { data, isPending, isError, error, refetch, isFetching } = useOrders(listParams);
  const quotes = data?.data ?? [];

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">استعلام‌های قیمت</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {data
            ? `${formatNumber(data.meta.total_count)} استعلام ثبت‌شده`
            : "مدیریت درخواست‌های استعلام B2C و B2B"}
        </p>
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center gap-2 text-sm font-bold text-foreground">
          <Filter set="light" size={18} primaryColor="#C22026" />
          فیلتر
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-muted-foreground">
              <Search set="light" size={18} />
            </span>
            <Input
              placeholder="جستجو کد پیگیری، نام یا موبایل..."
              className="ps-10"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Select value={status || "all"} onValueChange={(v) => setStatus(v === "all" ? "" : v)}>
            <SelectTrigger>
              <SelectValue placeholder="همه وضعیت‌ها" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه وضعیت‌ها</SelectItem>
              {INQUIRY_STATUSES.map((s) => (
                <SelectItem key={s} value={s}>
                  {STATUS_LABELS[s]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="p-0">
          {isPending ? (
            <div className="flex flex-col gap-3 p-6">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <p className="text-sm font-bold text-foreground">
                {error instanceof ApiError ? error.message : "خطا در دریافت استعلام‌ها"}
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                تلاش مجدد
              </Button>
            </div>
          ) : quotes.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <Document set="bulk" size={48} primaryColor="#BDBDBD" />
              <p className="text-sm font-bold text-foreground">استعلامی یافت نشد</p>
            </div>
          ) : (
            <ul className={`flex flex-col gap-1 p-3 ${isFetching ? "opacity-60" : ""}`}>
              {quotes.map((quote) => (
                <li
                  key={quote.id}
                  className="grid grid-cols-1 items-center gap-2 rounded-lg px-4 py-3 transition-colors hover:bg-muted/60 md:grid-cols-[1fr_1fr_120px_120px_88px] md:gap-4"
                >
                  <div>
                    <p className="text-sm font-bold text-foreground tnum">{quote.tracking_code}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(quote.created_at).toLocaleDateString("fa-IR")}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-foreground">{quote.customer_name}</p>
                    <p className="text-xs text-muted-foreground tnum">{quote.customer_phone}</p>
                  </div>
                  <span className="text-sm font-bold tnum">
                    {quote.estimated_total ? formatToman(quote.estimated_total) : "—"}
                  </span>
                  <Badge variant="outline">{quote.status_label}</Badge>
                  <div className="flex justify-end">
                    <Button asChild variant="ghost" size="sm">
                      <Link href={`/orders/${quote.id}`}>بررسی</Link>
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
