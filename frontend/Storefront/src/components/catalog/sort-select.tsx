"use client";

import type { ReactNode } from "react";
import { useCatalogParams } from "@/components/catalog/use-catalog-params";
import { CustomSelect } from "@/components/ui/custom-select";
import { cn, formatNumber } from "@/lib/utils";
import type { ProductSort } from "@/types/product";

/**
 * Sort options aligned to live API `sort` keys.
 * Stock / discount / popularity are filters or unsupported — do not invent keys.
 */
export const SORT_OPTIONS: { value: ProductSort; label: string }[] = [
  { value: "newest", label: "جدیدترین" },
  { value: "price_asc", label: "ارزان‌ترین" },
  { value: "price_desc", label: "گران‌ترین" },
  { value: "name_asc", label: "نام (الف تا ی)" },
  { value: "name_desc", label: "نام (ی تا الف)" },
];

/** Three-line sort glyph (Digikala-style structure, Karzar colors). */
function SortLinesIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      aria-hidden
    >
      <path
        d="M3 5h12M3 9h8M3 13h5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ProductCount({
  totalCount,
  isLoading,
  className,
}: {
  totalCount?: number;
  isLoading?: boolean;
  className?: string;
}) {
  return (
    <p
      className={cn("shrink-0 whitespace-nowrap text-sm text-[#9ca3af] tnum", className)}
      aria-live="polite"
    >
      {isLoading
        ? "…"
        : totalCount != null
          ? `${formatNumber(totalCount)} کالا`
          : null}
    </p>
  );
}

/** Closed trigger styles aligned with the mobile «فیلترها» chip. */
const MOBILE_SORT_TRIGGER =
  "h-auto min-h-11 w-auto max-w-full rounded-lg bg-card px-4 py-2.5 text-sm font-medium text-foreground shadow-soft ring-0";

export function SortSelect({
  totalCount,
  isLoading,
  mobileLeading,
}: {
  /** Live catalog `meta.total_count` for the «N کالا» counter. */
  totalCount?: number;
  isLoading?: boolean;
  /** Mobile-only control rendered before the sort dropdown (e.g. Filters). */
  mobileLeading?: ReactNode;
} = {}) {
  const { params, setParams } = useCatalogParams();
  const value =
    params.sort && SORT_OPTIONS.some((o) => o.value === params.sort)
      ? params.sort
      : "newest";

  return (
    <div dir="rtl">
      {/* Mobile: Filters + sort chip row; count pinned to physical left (ms-auto in RTL). */}
      <div className="flex w-full items-center gap-2 lg:hidden">
        {mobileLeading}
        <CustomSelect
          aria-label="مرتب‌سازی محصولات"
          value={value}
          onValueChange={(sort) => setParams({ sort })}
          options={SORT_OPTIONS}
          className="w-auto max-w-[9.5rem] shrink-0 sm:max-w-[11rem]"
          triggerClassName={MOBILE_SORT_TRIGGER}
        />
        <ProductCount
          totalCount={totalCount}
          isLoading={isLoading}
          className="ms-auto ps-2 pe-0.5"
        />
      </div>

      {/* Desktop: Digikala-style horizontal sort bar */}
      <div className="hidden w-full min-w-0 items-center justify-between gap-4 lg:flex">
        <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-4">
          <span className="inline-flex shrink-0 items-center gap-1.5 text-sm text-muted-foreground">
            <SortLinesIcon className="text-muted-foreground" />
            <span className="whitespace-nowrap font-medium">مرتب‌سازی:</span>
          </span>

          <div
            className="no-scrollbar h-scroll flex min-w-0 flex-1 items-stretch gap-3 sm:gap-5"
            role="radiogroup"
            aria-label="مرتب‌سازی محصولات"
          >
            {SORT_OPTIONS.map((opt) => {
              const active = value === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setParams({ sort: opt.value })}
                  className={cn(
                    "shrink-0 whitespace-nowrap px-1 py-2.5 text-sm transition-colors",
                    "min-h-11 touch-manipulation focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
                    active
                      ? "border-b-2 border-primary font-semibold text-primary"
                      : "border-b-2 border-transparent text-[#6b7280] hover:text-foreground",
                  )}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        <ProductCount totalCount={totalCount} isLoading={isLoading} />
      </div>
    </div>
  );
}
