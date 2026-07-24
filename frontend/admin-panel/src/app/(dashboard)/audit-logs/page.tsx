"use client";

import { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Danger, Document } from "react-iconly";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuditLogs } from "@/features/audit/queries";
import { ApiError } from "@/lib/api-client";
import { formatNumber } from "@/lib/utils";

const PAGE_SIZE = 30;

const ENTITY_TYPE_LABELS: Record<string, string> = {
  product: "محصول",
  order: "سفارش",
  user: "مشتری",
  category: "دسته‌بندی",
  brand: "برند",
  article: "مقاله",
  hero_slide: "اسلاید هدر",
};

const ACTION_LABELS: Record<string, string> = {
  soft_delete: "حذف نرم",
  delete: "حذف",
  update: "ویرایش",
  create: "ایجاد",
  restore: "بازیابی",
  archive: "بایگانی",
  stock_adjust: "تعدیل موجودی",
};

function entityLabel(type: string): string {
  return ENTITY_TYPE_LABELS[type] ?? type;
}

function actionLabel(action: string): string {
  return ACTION_LABELS[action] ?? action;
}

function actionBadgeVariant(action: string): "danger" | "warning" | "success" | "outline" {
  if (action.includes("delete") || action === "archive") return "danger";
  if (action === "update" || action === "stock_adjust") return "warning";
  if (action === "create" || action === "restore") return "success";
  return "outline";
}

export default function AuditLogsPage() {
  const [entityType, setEntityType] = useState("");
  const [skip, setSkip] = useState(0);

  // Reset pagination whenever the entity filter changes (adjust-state-on-render
  // pattern — avoids a cascading-render effect just to zero out `skip`).
  const [prevEntityType, setPrevEntityType] = useState(entityType);
  if (prevEntityType !== entityType) {
    setPrevEntityType(entityType);
    setSkip(0);
  }

  const listParams = useMemo(
    () => ({
      skip,
      limit: PAGE_SIZE,
      entity_type: entityType || undefined,
    }),
    [skip, entityType],
  );

  const { data, isPending, isError, error, refetch, isFetching } = useAuditLogs(listParams);
  const entries = data?.data ?? [];
  const meta = data?.meta;
  const rangeStart = meta ? Math.min(meta.skip + 1, meta.total_count) : 0;
  const rangeEnd = meta ? Math.min(meta.skip + meta.limit, meta.total_count) : 0;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-ink">گزارش ممیزی</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {data ? `${formatNumber(data.meta.total_count)} رویداد` : "تاریخچهٔ اقدامات حساس ادمین"}
          </p>
        </div>
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="max-w-xs">
          <Select value={entityType || "all"} onValueChange={(v) => setEntityType(v === "all" ? "" : v)}>
            <SelectTrigger>
              <SelectValue placeholder="همه موجودیت‌ها" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه موجودیت‌ها</SelectItem>
              {Object.entries(ENTITY_TYPE_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
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
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <Danger set="bulk" size={44} primaryColor="#C22026" />
              <p className="text-sm font-bold text-foreground">
                {error instanceof ApiError ? error.message : "خطا در دریافت گزارش ممیزی"}
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                تلاش مجدد
              </Button>
            </div>
          ) : entries.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <Document set="bulk" size={48} primaryColor="#BDBDBD" />
              <p className="text-sm font-bold text-foreground">رویدادی ثبت نشده است</p>
            </div>
          ) : (
            <div className="flex flex-col p-3">
              <ul className={`flex flex-col gap-1 ${isFetching ? "opacity-60" : ""}`}>
                {entries.map((entry) => (
                  <li
                    key={entry.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg px-4 py-3 transition-colors hover:bg-[#F7F7F7]"
                  >
                    <div className="flex min-w-0 flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={actionBadgeVariant(entry.action)}>
                          {actionLabel(entry.action)}
                        </Badge>
                        <span className="text-sm font-bold text-foreground">
                          {entityLabel(entry.entity_type)} #{entry.entity_id}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {entry.actor_user_id ? `توسط کاربر #${entry.actor_user_id}` : "سیستم"}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground tnum">
                      {new Date(entry.created_at).toLocaleString("fa-IR")}
                    </span>
                  </li>
                ))}
              </ul>

              {meta && meta.total_count > meta.limit && (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 pt-4">
                  <span className="text-xs text-muted-foreground tnum">
                    نمایش {formatNumber(rangeStart)} تا {formatNumber(rangeEnd)} از{" "}
                    {formatNumber(meta.total_count)} رویداد
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={!meta.has_prev || isFetching}
                      onClick={() => setSkip((prev) => Math.max(0, prev - PAGE_SIZE))}
                    >
                      <ArrowRight set="light" size={16} />
                      قبلی
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={!meta.has_next || isFetching}
                      onClick={() => setSkip((prev) => prev + PAGE_SIZE)}
                    >
                      بعدی
                      <ArrowLeft set="light" size={16} />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
