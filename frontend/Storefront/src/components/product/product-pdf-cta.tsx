"use client";

import { Document } from "react-iconly";
import { cn } from "@/lib/utils";
import type { ProductDetail } from "@/types/product";

/** EPIC-1.7 / FE-002 — PDF catalog CTA; hide entirely when URL missing. */
export function ProductPdfCta({
  product,
  className,
}: {
  product: ProductDetail;
  className?: string;
}) {
  const url = product.pdf_catalog_url?.trim() || null;
  if (!url) return null;

  return (
    <section
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-secondary/50 px-4 py-3.5 sm:px-5",
        className,
      )}
      aria-labelledby="pdp-pdf-heading"
    >
      <div className="min-w-0">
        <h2 id="pdp-pdf-heading" className="text-sm font-bold text-foreground">
          کاتالوگ / دیتاشیت PDF
        </h2>
        <p className="mt-0.5 text-[11px] text-muted-foreground">فایل رسمی محصول</p>
      </div>
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground transition-opacity hover:opacity-90"
      >
        <Document size="small" set="bold" aria-hidden />
        دانلود PDF
      </a>
    </section>
  );
}
