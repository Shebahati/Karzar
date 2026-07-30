"use client";

import { Document } from "react-iconly";
import type { ProductDetail } from "@/types/product";

/** EPIC-1.7 / FE-002 — PDF catalog CTA; honest empty when URL missing (Bible Conflict matrix). */
export function ProductPdfCta({ product }: { product: ProductDetail }) {
  const url = product.pdf_catalog_url?.trim() || null;

  return (
    <section
      className="mt-5 rounded-2xl border border-border/60 bg-card p-4 shadow-soft"
      aria-labelledby="pdp-pdf-heading"
    >
      <h2 id="pdp-pdf-heading" className="text-sm font-bold text-foreground">
        کاتالوگ / دیتاشیت PDF
      </h2>
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Document size="small" set="bold" aria-hidden />
          دانلود PDF
        </a>
      ) : (
        <p className="mt-2 text-sm leading-7 text-muted-foreground" role="status">
          کاتالوگ PDF برای این محصول هنوز در دسترس نیست.
        </p>
      )}
    </section>
  );
}
