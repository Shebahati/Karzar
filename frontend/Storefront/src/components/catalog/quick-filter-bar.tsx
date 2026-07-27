"use client";

import { useMemo } from "react";
import { useBrands } from "@/features/catalog/queries";
import { cn, toPersianDigits } from "@/lib/utils";
import { useCatalogParams } from "@/components/catalog/use-catalog-params";

const QUICK_BRAND_LIMIT = 6;

/**
 * Always-visible mobile filter shortcuts so a useful filter applies in ≤3 taps:
 * 1) open drawer → 2) tap chip → 3) confirm footer.
 */
export function QuickFilterBar() {
  const { params, setParams, toggleBrand } = useCatalogParams();
  const { data: brands, isLoading } = useBrands();
  const selectedBrandIds = params.brand_ids ?? [];
  const inStock = Boolean(params.in_stock);

  const topBrands = useMemo(() => {
    const list = brands ?? [];
    if (list.length === 0) return [];
    // Prefer selected brands first so active chips stay visible, then fill.
    const selected = list.filter((b) => selectedBrandIds.includes(b.id));
    const rest = list.filter((b) => !selectedBrandIds.includes(b.id));
    return [...selected, ...rest].slice(0, QUICK_BRAND_LIMIT);
  }, [brands, selectedBrandIds]);

  return (
    <div className="mb-4 space-y-2" dir="rtl">
      <p className="text-[11px] font-bold text-muted-foreground">فیلتر سریع</p>
      <div
        className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        role="group"
        aria-label="فیلتر سریع"
      >
        <QuickChip
          active={inStock}
          onClick={() => setParams({ in_stock: inStock ? null : "1" })}
          label="فقط موجود"
        />
        {isLoading ? (
          <span className="inline-flex min-h-10 items-center px-2 text-xs text-steel">
            در حال بارگذاری برندها…
          </span>
        ) : (
          topBrands.map((brand) => {
            const active = selectedBrandIds.includes(brand.id);
            return (
              <QuickChip
                key={brand.id}
                active={active}
                onClick={() => toggleBrand(brand.id)}
                label={brand.name}
              />
            );
          })
        )}
      </div>
      {selectedBrandIds.length > 0 ? (
        <p className="text-[11px] text-steel">
          {toPersianDigits(String(selectedBrandIds.length))} برند انتخاب شده — جزئیات در بخش
          «برند»
        </p>
      ) : null}
    </div>
  );
}

function QuickChip({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "inline-flex min-h-10 shrink-0 items-center rounded-xl px-3.5 text-xs font-bold transition-colors",
        active
          ? "bg-primary text-primary-foreground shadow-soft"
          : "bg-secondary text-secondary-foreground hover:bg-muted",
      )}
    >
      {label}
    </button>
  );
}
