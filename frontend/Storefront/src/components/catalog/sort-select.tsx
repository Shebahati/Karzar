"use client";

import { useCatalogParams } from "@/components/catalog/use-catalog-params";
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

export function SortSelect({
  totalCount,
  isLoading,
}: {
  /** Live catalog `meta.total_count` for the «N کالا» counter. */
  totalCount?: number;
  isLoading?: boolean;
} = {}) {
  const { params, setParams } = useCatalogParams();
  const value =
    params.sort && SORT_OPTIONS.some((o) => o.value === params.sort)
      ? params.sort
      : "newest";

  return (
    <div
      className="flex w-full min-w-0 items-center justify-between gap-4"
      dir="rtl"
    >
      <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-4">
        <span className="inline-flex shrink-0 items-center gap-1.5 text-sm text-muted-foreground">
          <SortLinesIcon className="text-muted-foreground" />
          <span className="whitespace-nowrap font-medium">مرتب‌سازی:</span>
        </span>

        <div
          className="no-scrollbar flex min-w-0 flex-1 items-stretch gap-3 overflow-x-auto sm:gap-5"
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

      <p
        className="shrink-0 whitespace-nowrap text-sm text-[#9ca3af] tnum"
        aria-live="polite"
      >
        {isLoading
          ? "…"
          : totalCount != null
            ? `${formatNumber(totalCount)} کالا`
            : null}
      </p>
    </div>
  );
}
