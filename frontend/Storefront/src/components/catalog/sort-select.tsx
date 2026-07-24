"use client";

import { useCatalogParams } from "@/components/catalog/use-catalog-params";
import { CustomSelect } from "@/components/ui/custom-select";
import type { ProductSort } from "@/types/product";

/** Storefront-facing sort options — practical for industrial catalog browsing. */
const OPTIONS: { value: ProductSort; label: string }[] = [
  { value: "newest", label: "جدیدترین" },
  { value: "price_asc", label: "ارزان‌ترین" },
  { value: "price_desc", label: "گران‌ترین" },
  { value: "discount_desc", label: "بیشترین تخفیف" },
  { value: "stock_first", label: "موجودها اول" },
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
