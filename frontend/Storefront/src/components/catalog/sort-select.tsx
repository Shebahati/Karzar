"use client";

import { useCatalogParams } from "@/components/catalog/use-catalog-params";
import { CustomSelect } from "@/components/ui/custom-select";
import type { ProductSort } from "@/types/product";

/**
 * Sort options aligned to live API `sort` keys.
 * Stock availability is a filter (`in_stock`), not a sort — API has no stock/discount ordering.
 */
const OPTIONS: { value: ProductSort; label: string }[] = [
  { value: "newest", label: "جدیدترین" },
  { value: "price_asc", label: "ارزان‌ترین" },
  { value: "price_desc", label: "گران‌ترین" },
];

export function SortSelect() {
  const { params, setParams } = useCatalogParams();
  const value = params.sort && OPTIONS.some((o) => o.value === params.sort)
    ? params.sort
    : "newest";

  return (
    <CustomSelect
      aria-label="مرتب‌سازی محصولات"
      value={value}
      onValueChange={(sort) => setParams({ sort })}
      options={OPTIONS}
      className="min-w-[11rem]"
    />
  );
}
