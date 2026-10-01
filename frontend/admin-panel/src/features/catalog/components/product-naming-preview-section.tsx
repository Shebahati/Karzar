"use client";

import type { ReactNode } from "react";
import { Document } from "react-iconly";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useProductNamingPreview } from "@/features/catalog/queries";
import type { ProductNamingPreview } from "@/types/product";

function confidenceBadge(confidence: string) {
  const c = confidence.toLowerCase();
  if (c === "high") return <Badge className="bg-emerald-600">HIGH</Badge>;
  if (c === "medium") return <Badge className="bg-amber-500">MEDIUM</Badge>;
  return <Badge variant="neutral">{confidence.toUpperCase()}</Badge>;
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[10rem_1fr] sm:gap-3">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm text-[#4F4F4F]">{children}</dd>
    </div>
  );
}

function PreviewBody({ data }: { data: ProductNamingPreview }) {
  const oemLabel =
    data.manufacturer_code_status === "verified" && data.manufacturer_code
      ? data.manufacturer_code
      : "تأیید نشده / ثبت نشده";
  const ptLabel = data.product_type
    ? `${data.product_type.name_fa} (${data.product_type.code})`
    : "تعیین نشده";

  return (
    <dl className="flex flex-col gap-3">
      <Row label="نام فعلی">{data.current_name}</Row>
      <Row label="Product Type">{ptLabel}</Row>
      <Row label="برند">{data.brand?.name ?? "—"}</Row>
      <Row label="کد سازنده">
        <span className="font-mono" dir="ltr">
          {oemLabel}
        </span>
      </Row>
      <Row label="Naming profile">
        <span dir="ltr">
          {data.profile ?? "—"}
          {data.profile_resolution ? ` · ${data.profile_resolution}` : ""}
        </span>
      </Row>
      <Row label="نام استاندارد پیشنهادی">
        {data.proposed_name ? (
          <span className="font-medium">{data.proposed_name}</span>
        ) : (
          <span className="text-muted-foreground">پیشنهادی در دسترس نیست (HOLD)</span>
        )}
      </Row>
      <Row label="وضعیت">
        <span dir="ltr">{data.state}</span>
      </Row>
      <Row label="سطح اطمینان">{confidenceBadge(data.confidence)}</Row>
      {data.reason_codes.length > 0 ? (
        <Row label="موانع / دلایل">
          <ul className="list-inside list-disc" dir="ltr">
            {data.reason_codes.map((code) => (
              <li key={code}>{code}</li>
            ))}
          </ul>
        </Row>
      ) : null}
      {data.warnings.length > 0 ? (
        <Row label="هشدارها">
          <ul className="list-inside list-disc" dir="ltr">
            {data.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Row>
      ) : null}
      <p className="mt-2 text-xs text-muted-foreground">
        پیش‌نمایش فقط‌خواندنی است؛ در این مرحله امکان ذخیره یا تغییر نام محصول از این پنل وجود ندارد.
      </p>
    </dl>
  );
}

/** Read-only Naming Standard preview — GET /products/{id}/naming-preview. No Apply. */
export function ProductNamingPreviewSection({ productId }: { productId: number }) {
  const { data, isPending, isError } = useProductNamingPreview(productId, productId > 0);

  return (
    <Card className="border-transparent shadow-card">
      <CardHeader className="flex-row items-center gap-2">
        <Document set="bulk" size={22} primaryColor="#D02327" />
        <CardTitle className="text-[#4F4F4F]">نام استاندارد کارزار</CardTitle>
      </CardHeader>
      <CardContent>
        {isPending ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : isError ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            دریافت پیش‌نمایش نام استاندارد ناموفق بود.
          </p>
        ) : data ? (
          <PreviewBody data={data} />
        ) : null}
      </CardContent>
    </Card>
  );
}
