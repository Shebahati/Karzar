"use client";

import { useMemo } from "react";
import { useProductsByIds } from "@/features/catalog/queries";
import { ProductCarousel } from "@/components/home/product-carousel";
import type { ProductDetail, SpecItem } from "@/types/product";

type AccessoryEntry = number | string | SpecItem;

function parseAccessoryIds(raw: unknown): number[] {
  if (!Array.isArray(raw)) return [];
  const ids: number[] = [];
  for (const item of raw as AccessoryEntry[]) {
    if (typeof item === "number" && Number.isFinite(item)) {
      ids.push(item);
      continue;
    }
    if (typeof item === "string") {
      const n = Number(item.trim());
      if (Number.isFinite(n) && n > 0) ids.push(n);
      continue;
    }
    if (item && typeof item === "object" && "value" in item) {
      const n = Number(String((item as SpecItem).value).trim());
      if (Number.isFinite(n) && n > 0) ids.push(n);
    }
  }
  return [...new Set(ids)];
}

function accessoryLabels(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  const labels: string[] = [];
  for (const item of raw as AccessoryEntry[]) {
    if (typeof item === "string" && item.trim() && Number.isNaN(Number(item.trim()))) {
      labels.push(item.trim());
      continue;
    }
    if (item && typeof item === "object" && "key" in item && "value" in item) {
      const row = item as SpecItem;
      const k = row.key?.trim();
      const v = String(row.value ?? "").trim();
      if (k && v) labels.push(`${k}: ${v}`);
      else if (v && Number.isNaN(Number(v))) labels.push(v);
    }
  }
  return labels;
}

/** EPIC-1.7 / FE-002 — accessories slot; always visible; empty OK (Bible: surface honest empty). */
export function ProductAccessoriesSlot({ product }: { product: ProductDetail }) {
  const raw = product.specifications?.optional_accessories ?? [];

  const ids = useMemo(() => parseAccessoryIds(raw), [raw]);
  const labels = useMemo(() => accessoryLabels(raw), [raw]);
  const { data: products, isLoading } = useProductsByIds(ids);

  const hasProductCards = ids.length > 0;
  const hasLabelsOnly = !hasProductCards && labels.length > 0;
  const isEmpty = !hasProductCards && !hasLabelsOnly;

  return (
    <section className="mt-12 sm:mt-20" aria-labelledby="pdp-accessories-heading">
      <h2
        id="pdp-accessories-heading"
        className="mb-5 flex items-center gap-2.5 text-lg font-bold text-foreground sm:text-xl"
      >
        <span className="h-6 w-1.5 rounded-full bg-primary" aria-hidden />
        لوازم جانبی پیشنهادی
      </h2>
      {isEmpty ? (
        <p
          className="rounded-2xl border border-dashed border-steel/20 bg-secondary/30 px-4 py-7 text-sm leading-7 text-muted-foreground"
          role="status"
        >
          لوازم جانبی ثبت‌شده‌ای برای این محصول نیست.
        </p>
      ) : null}
      {hasLabelsOnly ? (
        <ul className="list-inside list-disc space-y-2 rounded-2xl bg-secondary/40 px-4 py-4 text-sm text-foreground">
          {labels.map((label) => (
            <li key={label}>{label}</li>
          ))}
        </ul>
      ) : null}
      {hasProductCards ? (
        <ProductCarousel products={products ?? []} isLoading={isLoading} />
      ) : null}
    </section>
  );
}
