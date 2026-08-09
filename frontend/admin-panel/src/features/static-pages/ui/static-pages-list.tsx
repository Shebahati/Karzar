"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Document } from "react-iconly";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { staticPagesService } from "@/services/static-pages";
import {
  STATIC_PAGE_META,
  type StaticPageDocument,
  type StaticPageSlug,
} from "@/types/static-pages";

function formatFaDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("fa-IR");
  } catch {
    return iso;
  }
}

export function StaticPagesList() {
  const [pages, setPages] = useState<StaticPageDocument[] | null>(null);

  useEffect(() => {
    setPages(staticPagesService.list());
  }, []);

  if (!pages) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-[#4F4F4F]">
          مدیریت محتوای صفحات
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          پیش‌نویس تماس، درباره ما، قوانین و حریم شخصی — ذخیره محلی در این مرورگر
        </p>
      </div>

      <div className="rounded-2xl border border-amber-200/80 bg-amber-50/80 px-4 py-3 text-sm leading-7 text-amber-950">
        <p className="font-bold">صفحات زنده فروشگاه هنوز از این ویرایشگر خوانده نمی‌شوند.</p>
        <p className="mt-1 text-amber-900/90">
          محتوای فعلی Contact / About / Terms / Privacy در فرانت فروشگاه hardcode است.
          تغییرات اینجا فقط به‌صورت پیش‌نویس محلی ذخیره می‌شود تا پس از اتصال backend
          (یا انتشار JSON مشابه صفحه هوم) منتشر شوند.
        </p>
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="divide-y divide-gray-100 p-0">
          {pages.map((page) => {
            const meta = STATIC_PAGE_META[page.slug as StaticPageSlug];
            return (
              <Link
                key={page.slug}
                href={`/cms/static-pages/${page.slug}`}
                className="flex items-start gap-4 px-4 py-4 transition-colors hover:bg-muted/40"
              >
                <span className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#D02327]/[0.08] text-primary">
                  <Document set="light" size={20} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-bold text-[#4F4F4F]">
                      {meta.label}
                    </span>
                    <Badge variant="outline" className="text-[10px]" dir="ltr">
                      {meta.hrefPreview}
                    </Badge>
                    <Badge
                      variant="outline"
                      className="border-amber-300 bg-amber-50 text-[10px] text-amber-800"
                    >
                      پیش‌نویس محلی
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {meta.description}
                  </p>
                  <p className="mt-1.5 text-[11px] text-muted-foreground">
                    {page.sections.length} بخش · آخرین ذخیره:{" "}
                    {formatFaDate(page.updatedAt)}
                  </p>
                </div>
                <span className="shrink-0 self-center text-xs font-bold text-primary">
                  ویرایش
                </span>
              </Link>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
