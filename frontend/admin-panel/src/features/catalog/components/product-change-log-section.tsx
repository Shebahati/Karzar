"use client";

import { useMemo, useState } from "react";
import { TimeCircle } from "react-iconly";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useProductChangeLog } from "@/features/catalog/queries";
import { formatToman } from "@/lib/utils";

const FIELD_LABELS: Record<string, string> = {
  stock_quantity: "موجودی",
  base_price: "قیمت پایه",
  original_price: "قیمت قبل از تخفیف",
  is_active: "وضعیت فعال",
  sku: "کد محصول",
  name: "نام محصول",
};

const PRICE_FIELDS = new Set(["base_price", "original_price"]);
const STOCK_FIELDS = new Set(["stock_quantity"]);

type ChangeFilter = "all" | "price" | "stock" | "other";

function fieldLabel(field: string): string {
  return FIELD_LABELS[field] ?? field;
}

function displayValue(field: string, value: string | null): string {
  if (value === null) return "—";
  if (field === "base_price" || field === "original_price") return formatToman(value);
  return value;
}

function matchesFilter(field: string, filter: ChangeFilter): boolean {
  if (filter === "all") return true;
  if (filter === "price") return PRICE_FIELDS.has(field);
  if (filter === "stock") return STOCK_FIELDS.has(field);
  return !PRICE_FIELDS.has(field) && !STOCK_FIELDS.has(field);
}

/** Read-only price/stock change history for a product — GET /products/{id}/change-log. */
export function ProductChangeLogSection({ productId }: { productId: number }) {
  const { data, isPending, isError } = useProductChangeLog(productId, productId > 0);
  const [filter, setFilter] = useState<ChangeFilter>("all");
  const entries = data?.data ?? [];

  const filtered = useMemo(
    () => entries.filter((entry) => matchesFilter(entry.field_name, filter)),
    [entries, filter],
  );

  return (
    <Card className="border-transparent shadow-card">
      <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <TimeCircle set="bulk" size={22} primaryColor="#C22026" />
          <CardTitle className="text-[#4F4F4F]">تاریخچه تغییرات</CardTitle>
        </div>
        <Select value={filter} onValueChange={(v) => setFilter(v as ChangeFilter)}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="فیلتر" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همه تغییرات</SelectItem>
            <SelectItem value="price">فقط قیمت</SelectItem>
            <SelectItem value="stock">فقط موجودی</SelectItem>
            <SelectItem value="other">سایر</SelectItem>
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent>
        {isPending ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : isError ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            دریافت تاریخچه تغییرات ناموفق بود.
          </p>
        ) : entries.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            هنوز تغییری برای این محصول ثبت نشده است.
          </p>
        ) : filtered.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            موردی با این فیلتر یافت نشد.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {filtered.map((entry) => (
              <li key={entry.id} className="flex flex-col gap-1.5 py-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Badge variant="outline">{fieldLabel(entry.field_name)}</Badge>
                  <span className="text-xs text-muted-foreground tnum">
                    {new Date(entry.created_at).toLocaleString("fa-IR")}
                  </span>
                </div>
                <p className="tnum text-foreground">
                  <span className="text-muted-foreground line-through">
                    {displayValue(entry.field_name, entry.old_value)}
                  </span>
                  {" ← "}
                  <span className="font-bold">{displayValue(entry.field_name, entry.new_value)}</span>
                </p>
                {entry.reason && (
                  <p className="text-xs text-muted-foreground">دلیل: {entry.reason}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
