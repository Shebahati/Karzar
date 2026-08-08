"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ChevronDown, Document, Download, Plus, Search } from "react-iconly";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useIssuedProformas,
  useRemoveIssuedProforma,
} from "@/features/invoices/queries";
import {
  buildInvoicePreviewHtml,
  downloadAdminInvoicePdf,
} from "@/lib/invoice-pdf";
import { cn, formatNumber, formatToman, toPersianDigits } from "@/lib/utils";
import type { IssuedProformaRecord } from "@/types/invoice-doc";

function formatFaDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return toPersianDigits(iso.slice(0, 16));
  return new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

function ProformaPreview({ record }: { record: IssuedProformaRecord }) {
  const html = useMemo(
    () => buildInvoicePreviewHtml(record.document),
    [record.document],
  );

  return (
    <div className="overflow-hidden rounded-xl border border-[#F0C4C5]/40] bg-[#F7F7F7]">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#EFEFEF] bg-white px-4 py-3">
        <div>
          <p className="text-sm font-bold text-[#4F4F4F]">
            {record.document.kind === "proforma" ? "پیش‌فاکتور" : "فاکتور"}{" "}
            <span className="tnum" dir="ltr">
              {record.refCode}
            </span>
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {record.lineCount} قلم · {formatToman(record.grandTotalToman)}
          </p>
        </div>
        {record.document.adminNote ? (
          <p className="max-w-md text-xs text-muted-foreground">
            یادداشت: {record.document.adminNote}
          </p>
        ) : null}
      </div>
      <div className="max-h-[70vh] overflow-auto p-3">
        <iframe
          title={`پیش‌نمایش ${record.refCode}`}
          srcDoc={html}
          className="min-h-[720px] w-full rounded-lg bg-white"
          sandbox="allow-same-origin"
        />
      </div>
      <div className="space-y-2 border-t border-[#EFEFEF] bg-white px-4 py-3 text-xs leading-6 text-muted-foreground">
        <p>
          خریدار: <span className="font-bold text-foreground">{record.buyerName}</span>
          {record.buyerPhone ? (
            <>
              {" "}
              · <span className="tnum" dir="ltr">{toPersianDigits(record.buyerPhone)}</span>
            </>
          ) : null}
        </p>
        {record.buyerAddress ? <p>آدرس: {record.buyerAddress}</p> : null}
        <ul className="divide-y divide-[#F0F0F0] rounded-lg bg-[#FAFAFA]">
          {record.document.lines.map((line, i) => (
            <li
              key={`${line.sku}-${i}`}
              className="flex flex-wrap items-center justify-between gap-2 px-3 py-2"
            >
              <span className="font-medium text-foreground">
                {toPersianDigits(i + 1)}. {line.name}
                {line.sku ? (
                  <span className="ms-2 text-[11px] text-muted-foreground" dir="ltr">
                    {line.sku}
                  </span>
                ) : null}
              </span>
              <span className="tnum text-muted-foreground">
                {toPersianDigits(line.quantity)} × {formatNumber(line.unitPriceToman)} تومان
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function IssuedProformasList() {
  const { data, isPending, refetch, isFetching } = useIssuedProformas();
  const removeMutation = useRemoveIssuedProforma();
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const rows = useMemo(() => {
    const list = data ?? [];
    const q = search.trim().toLowerCase();
    if (!q) return list;
    return list.filter((r) => {
      const hay = [
        r.refCode,
        r.buyerName,
        r.buyerPhone,
        r.buyerAddress,
        r.document.buyer.fullName,
        r.document.buyer.companyName,
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [data, search]);

  async function handleDownload(record: IssuedProformaRecord) {
    setDownloadingId(record.id);
    try {
      await downloadAdminInvoicePdf(record.document);
      toast.success("پنجره چاپ / PDF باز شد");
    } catch (err) {
      const code = err instanceof Error ? err.message : "";
      if (code === "POPUP_BLOCKED") {
        toast.error("پاپ‌آپ مسدود است — اجازه را در مرورگر فعال کنید");
      } else {
        toast.error("خطا در دانلود");
      }
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[#4F4F4F]">پیش‌فاکتورهای صادر شده</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            فهرست محلی پیش‌فاکتورهایی که از فاکتورساز در همین مرورگر تولید شده‌اند.
            همگام‌سازی بین ادمین‌ها نیاز به endpoint سمت سرور دارد و فعلاً فعال نیست.
          </p>
        </div>
        <Button asChild size="sm">
          <Link href="/finance/invoice-builder">
            <Plus set="light" size={16} />
            فاکتورساز
          </Link>
        </Button>
      </div>

      <div className="rounded-xl border border-[#F0C4C5]/50] bg-[#FDF5F5] px-4 py-3 text-sm text-[#4F4F4F]">
        ذخیره فعلی: <span className="font-bold">localStorage</span> این دستگاه — با پاک
        کردن داده‌های سایت یا تعویض مرورگر از بین می‌رود. بعد از آماده‌شدن API فقط لایه
        سرویس عوض می‌شود.
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="relative max-w-md">
          <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-muted-foreground">
            <Search set="light" size={18} />
          </span>
          <Input
            placeholder="جستجو خریدار، موبایل یا شماره…"
            className="ps-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="p-0">
          {isPending ? (
            <div className="flex flex-col gap-3 p-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <Document set="bulk" size={48} primaryColor="#BDBDBD" />
              <p className="text-sm font-bold text-foreground">پیش‌فاکتوری ثبت نشده</p>
              <p className="max-w-sm text-xs text-muted-foreground">
                از فاکتورساز یک پیش‌فاکتور بسازید تا اینجا ظاهر شود.
              </p>
              <Button asChild variant="outline" size="sm">
                <Link href="/finance/invoice-builder">رفتن به فاکتورساز</Link>
              </Button>
            </div>
          ) : (
            <div className={cn("flex flex-col p-3", isFetching && "opacity-70")}>
              <div className="hidden px-4 py-2 text-xs font-bold text-muted-foreground md:grid md:grid-cols-[1.1fr_1.2fr_1fr_100px_160px] md:gap-3">
                <span>شماره</span>
                <span>خریدار</span>
                <span>زمان صدور</span>
                <span>مبلغ</span>
                <span />
              </div>
              <ul className="flex flex-col gap-1">
                {rows.map((row) => {
                  const open = expandedId === row.id;
                  return (
                    <li key={row.id} className="rounded-lg">
                      <div className="grid grid-cols-1 items-center gap-2 px-4 py-3 transition-colors hover:bg-[#F7F7F7] md:grid-cols-[1.1fr_1.2fr_1fr_100px_160px] md:gap-3">
                        <div>
                          <p className="text-sm font-bold text-[#4F4F4F] tnum" dir="ltr">
                            {row.refCode}
                          </p>
                          <Badge variant="neutral" className="mt-1 text-[10px]">
                            {row.document.kind === "proforma" ? "پیش‌فاکتور" : "فاکتور"}
                          </Badge>
                        </div>
                        <div>
                          <p className="text-sm font-bold text-foreground">{row.buyerName}</p>
                          {row.buyerPhone ? (
                            <p className="text-xs text-muted-foreground tnum" dir="ltr">
                              {toPersianDigits(row.buyerPhone)}
                            </p>
                          ) : null}
                        </div>
                        <p className="text-xs text-muted-foreground tnum">
                          {formatFaDateTime(row.createdAt)}
                        </p>
                        <p className="text-sm font-bold text-[#4F4F4F] tnum">
                          {formatToman(row.grandTotalToman)}
                        </p>
                        <div className="flex flex-wrap items-center justify-end gap-1">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={downloadingId === row.id}
                            onClick={() => void handleDownload(row)}
                            className="gap-1"
                          >
                            <Download set="light" size={14} />
                            دانلود
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            aria-expanded={open}
                            onClick={() =>
                              setExpandedId((id) => (id === row.id ? null : row.id))
                            }
                            className="gap-1"
                          >
                            <span
                              className={cn(
                                "inline-flex transition-transform",
                                open && "rotate-180",
                              )}
                            >
                              <ChevronDown set="light" size={16} />
                            </span>
                            جزئیات
                          </Button>
                        </div>
                      </div>
                      {open ? (
                        <div className="space-y-3 px-3 pb-4">
                          <ProformaPreview record={row} />
                          <div className="flex justify-end">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="text-destructive"
                              disabled={removeMutation.isPending}
                              onClick={() => {
                                void removeMutation.mutateAsync(row.id).then(() => {
                                  toast.success("از فهرست محلی حذف شد");
                                  setExpandedId(null);
                                  void refetch();
                                });
                              }}
                            >
                              حذف از فهرست محلی
                            </Button>
                          </div>
                        </div>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
