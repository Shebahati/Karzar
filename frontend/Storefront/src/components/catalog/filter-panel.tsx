"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, CloseSquare, Search, TickSquare } from "react-iconly";
import { Checkbox } from "@/components/ui/checkbox";
import { cn, formatNumber, toPersianDigits } from "@/lib/utils";
import { useBrands, useSpecFilterOptions } from "@/features/catalog/queries";
import { useFeatureLabel } from "@/lib/feature-labels";
import { AccordionFilter } from "@/components/catalog/accordion-filter";
import { CategoryTreeFilter } from "@/components/catalog/category-tree-filter";
import {
  FILTER_BRAND_PREVIEW,
  FilterShowMoreButton,
  useFilterShowMore,
} from "@/components/catalog/filter-show-more";
import { PriceRangeSlider } from "@/components/catalog/price-range-slider";
import { useCatalogPriceDomain } from "@/components/catalog/use-catalog-price-domain";
import {
  encodeCountryList,
  useCatalogParams,
} from "@/components/catalog/use-catalog-params";
import type { ProductListParams, ProductSummary } from "@/types/product";

type FilterAccordionKey =
  | "category"
  | "brand"
  | "country"
  | "price"
  | "stock"
  | "specs";

/** Shared filter UI rendered inside the desktop sidebar and the mobile drawer. */
export function FilterPanel({
  onApplied,
  /** When true, each change notifies parent (legacy). Prefer false + footer CTA on mobile. */
  notifyOnChange = false,
  /** Kept for callers; accordion sections always start collapsed. */
  mobileDefaults: _mobileDefaults = false,
  /** Hub pages lock a category in the path — clear must leave the hub. */
  lockedCategoryId,
  /**
   * `sidebar`: sticky column; filters grow with content (page scrolls).
   * `stack` (default): plain flow for the mobile drawer (drawer owns overflow).
   */
  layout = "stack",
  /** Products currently shown on the PLP — folded into the price slider domain. */
  priceSeedProducts = [],
}: {
  onApplied?: () => void;
  notifyOnChange?: boolean;
  mobileDefaults?: boolean;
  lockedCategoryId?: number;
  layout?: "stack" | "sidebar";
  priceSeedProducts?: Pick<ProductSummary, "base_price">[];
}) {
  const {
    params,
    setParams,
    setSpecFilter,
    toggleBrand,
    toggleCountry,
    clearAll,
    unlockToCatalog,
    applyCategory,
    activeCount,
  } = useCatalogParams();
  const { data: brands, isLoading: brandsLoading } = useBrands();
  const effectiveCategoryId = params.category_id ?? lockedCategoryId;
  const { data: specOptions } = useSpecFilterOptions(effectiveCategoryId ?? 0);

  const [brandQuery, setBrandQuery] = useState("");
  const [openSections, setOpenSections] = useState<
    Partial<Record<FilterAccordionKey, boolean>>
  >({});

  const notify = () => {
    if (notifyOnChange) onApplied?.();
  };

  const isSectionOpen = (key: FilterAccordionKey) => openSections[key] ?? false;
  const setSectionOpen = (key: FilterAccordionKey, open: boolean) => {
    setOpenSections((prev) => ({ ...prev, [key]: open }));
  };

  const selectedBrandIds = params.brand_ids ?? [];
  const selectedCountries = params.countries ?? [];

  const countries = useMemo(
    () =>
      Array.from(
        new Set((brands ?? []).map((b) => b.country).filter(Boolean)),
      ).sort((a, b) => String(a).localeCompare(String(b), "fa")) as string[],
    [brands],
  );

  // Drop invalid countries from URL once brands are known.
  useEffect(() => {
    if (brandsLoading || !brands || selectedCountries.length === 0) return;
    const validSet = new Set(
      brands.map((b) => b.country).filter(Boolean) as string[],
    );
    const next = selectedCountries.filter((c) => validSet.has(c));
    if (next.length !== selectedCountries.length) {
      setParams({ country: encodeCountryList(next) });
    }
  }, [brands, brandsLoading, selectedCountries, setParams]);

  const filteredBrands = useMemo(() => {
    const q = brandQuery.trim().toLowerCase();
    const list = brands ?? [];
    if (!q) return list;
    return list.filter(
      (b) =>
        b.name.toLowerCase().includes(q) ||
        (b.country ?? "").toLowerCase().includes(q),
    );
  }, [brands, brandQuery]);

  const brandShowMore = useFilterShowMore(
    filteredBrands.length,
    brandQuery,
    FILTER_BRAND_PREVIEW,
  );
  const countryShowMore = useFilterShowMore(countries.length);

  const priceDomainParams = useMemo<ProductListParams>(() => {
    const next: ProductListParams = {
      category_id: effectiveCategoryId,
      brand_ids: params.brand_ids,
      countries: params.countries,
      search: params.search,
      in_stock: params.in_stock,
      on_sale: params.on_sale,
      spec_filters: params.spec_filters,
    };
    return next;
  }, [
    effectiveCategoryId,
    params.brand_ids,
    params.countries,
    params.search,
    params.in_stock,
    params.on_sale,
    params.spec_filters,
  ]);

  const { absoluteMin, absoluteMax } = useCatalogPriceDomain(
    priceDomainParams,
    priceSeedProducts,
  );

  const priceMin = Math.min(
    absoluteMax,
    Math.max(absoluteMin, params.min_price ?? absoluteMin),
  );
  const priceMax = Math.max(
    priceMin,
    Math.min(absoluteMax, params.max_price ?? absoluteMax),
  );

  /** URL `category` → product list API `category_id` (incl. L1/L2/L3; API expands subtree). */
  const selectCategory = (id: number | null) => {
    applyCategory(id, { lockedCategoryId });
    notify();
  };

  const handleClearAll = () => {
    if (lockedCategoryId != null) {
      unlockToCatalog({ preserveFacets: false });
    } else {
      clearAll();
    }
    setBrandQuery("");
    notify();
  };

  const isSidebar = layout === "sidebar";

  const accordionKeys = useMemo((): FilterAccordionKey[] => {
    const keys: FilterAccordionKey[] = ["category", "brand"];
    if (countries.length > 0) keys.push("country");
    keys.push("price", "stock");
    if (specOptions && Object.keys(specOptions.technical_specs).length > 0) {
      keys.push("specs");
    }
    return keys;
  }, [countries.length, specOptions]);

  const allAccordionsOpen = accordionKeys.every((key) => isSectionOpen(key));

  const toggleAllAccordions = () => {
    const next = !allAccordionsOpen;
    setOpenSections((prev) => {
      const updated = { ...prev };
      for (const key of accordionKeys) updated[key] = next;
      return updated;
    });
  };

  const header = (
    <div
      className={cn(
        // End inset = AccordionFilter chrome: 1px card border + px-4 (was me-3.5 on the
        // button — too weak / unreliable vs parent pe).
        "flex items-center justify-between gap-2 ps-0.5 pe-[17px]",
        isSidebar && "bg-background pb-3",
      )}
    >
      <div className="flex min-w-0 items-center gap-1.5">
        <h2 className="text-base font-bold tracking-tight text-foreground">فیلترها</h2>
        {(activeCount > 0 || lockedCategoryId != null) && (
          <button
            type="button"
            onClick={handleClearAll}
            className="inline-flex min-h-11 items-center gap-1 rounded-lg px-2 text-xs font-bold text-primary hover:bg-accent"
          >
            <CloseSquare size="small" set="light" />
            حذف همه ({formatNumber(Math.max(activeCount, lockedCategoryId != null ? 1 : 0))})
          </button>
        )}
      </div>
      <button
        type="button"
        onClick={toggleAllAccordions}
        aria-expanded={allAccordionsOpen}
        aria-label={allAccordionsOpen ? "بستن همه فیلترها" : "باز کردن همه فیلترها"}
        className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-colors hover:bg-primary/90"
      >
        <span
          className={cn(
            "grid place-items-center transition-transform duration-300 ease-out",
            allAccordionsOpen && "rotate-180",
          )}
          aria-hidden
        >
          <ChevronDown size="small" set="bold" primaryColor="currentColor" />
        </span>
      </button>
    </div>
  );

  const body = (
    <>
      <CategoryTreeFilter
        activeId={effectiveCategoryId ?? null}
        onSelect={(id) => selectCategory(id)}
        onClear={() => selectCategory(null)}
        open={isSectionOpen("category")}
        onOpenChange={(open) => setSectionOpen("category", open)}
      />

      <AccordionFilter
        title="برند"
        hint={
          selectedBrandIds.length > 0
            ? `${toPersianDigits(selectedBrandIds.length)} برند انتخاب شده`
            : undefined
        }
        badge={selectedBrandIds.length ? toPersianDigits(selectedBrandIds.length) : undefined}
        open={isSectionOpen("brand")}
        onOpenChange={(open) => setSectionOpen("brand", open)}
      >
        {(brands?.length ?? 0) > 6 && (
          <div className="relative mb-3">
            <span className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-muted-foreground">
              <Search size="small" set="light" />
            </span>
            <input
              value={brandQuery}
              onChange={(e) => setBrandQuery(e.target.value)}
              placeholder="جستجوی برند…"
              aria-label="جستجوی برند"
              className="h-11 w-full rounded-xl bg-input ps-9 pe-3 text-base outline-none focus:ring-2 focus:ring-ring/40 md:text-sm"
            />
          </div>
        )}
        {selectedBrandIds.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {selectedBrandIds.map((id) => {
              const name = brands?.find((b) => b.id === id)?.name ?? `#${id}`;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => {
                    toggleBrand(id);
                    notify();
                  }}
                  aria-label={`حذف برند ${name}`}
                  className="inline-flex min-h-9 items-center gap-1 rounded-lg bg-accent px-2.5 text-[11px] font-bold text-primary"
                >
                  {name}
                  <CloseSquare size={14} set="bold" primaryColor="#D02327" aria-hidden />
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => {
                setParams({ brand: null });
                notify();
              }}
              className="inline-flex min-h-9 items-center px-2 text-[11px] font-bold text-steel hover:text-primary"
            >
              پاک کردن برندها
            </button>
          </div>
        )}
        <div className="space-y-0.5 pe-1" role="group" aria-label="برندها">
          {brandsLoading ? (
            <p className="px-2 py-3 text-xs text-steel">در حال بارگذاری برندها…</p>
          ) : (
            <>
              {filteredBrands.slice(0, brandShowMore.visibleCount).map((b) => {
                const active = selectedBrandIds.includes(b.id);
                return (
                  <MultiSelectRow
                    key={b.id}
                    active={active}
                    onClick={() => {
                      toggleBrand(b.id);
                      notify();
                    }}
                    label={b.name}
                    meta={b.country ?? undefined}
                  />
                );
              })}
              {brandShowMore.canShowMore ? (
                <FilterShowMoreButton
                  remaining={brandShowMore.remaining}
                  onClick={brandShowMore.showMore}
                />
              ) : null}
              {filteredBrands.length === 0 && (
                <p className="px-2 py-3 text-xs text-steel">برندی یافت نشد.</p>
              )}
            </>
          )}
        </div>
      </AccordionFilter>

      {countries.length > 0 && (
        <AccordionFilter
          title="کشور سازنده"
          hint={
            selectedCountries.length > 0
              ? `${toPersianDigits(selectedCountries.length)} کشور انتخاب شده`
              : undefined
          }
          badge={
            selectedCountries.length
              ? toPersianDigits(selectedCountries.length)
              : undefined
          }
          open={isSectionOpen("country")}
          onOpenChange={(open) => setSectionOpen("country", open)}
        >
          {selectedCountries.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-1.5">
              {selectedCountries.map((country) => (
                <button
                  key={country}
                  type="button"
                  onClick={() => {
                    toggleCountry(country);
                    notify();
                  }}
                  aria-label={`حذف کشور ${country}`}
                  className="inline-flex min-h-9 items-center gap-1 rounded-lg bg-accent px-2.5 text-[11px] font-bold text-primary"
                >
                  {country}
                  <CloseSquare size={14} set="bold" primaryColor="#D02327" aria-hidden />
                </button>
              ))}
              <button
                type="button"
                onClick={() => {
                  setParams({ country: null });
                  notify();
                }}
                className="inline-flex min-h-9 items-center px-2 text-[11px] font-bold text-steel hover:text-primary"
              >
                پاک کردن کشورها
              </button>
            </div>
          )}
          <div className="flex flex-wrap gap-2" role="group" aria-label="کشور سازنده">
            {countries.slice(0, countryShowMore.visibleCount).map((country) => {
              const active = selectedCountries.includes(country);
              return (
                <button
                  key={country}
                  type="button"
                  aria-pressed={active}
                  onClick={() => {
                    toggleCountry(country);
                    notify();
                  }}
                  className={cn(
                    "inline-flex min-h-11 items-center rounded-xl px-3.5 py-2 text-xs font-bold transition-colors",
                    active
                      ? "bg-primary text-primary-foreground shadow-soft"
                      : "bg-secondary text-secondary-foreground hover:bg-muted",
                  )}
                >
                  {country}
                </button>
              );
            })}
          </div>
          {countryShowMore.canShowMore ? (
            <FilterShowMoreButton
              remaining={countryShowMore.remaining}
              onClick={countryShowMore.showMore}
            />
          ) : null}
        </AccordionFilter>
      )}

      <AccordionFilter
        title="محدوده قیمت"
        hint="تومان"
        open={isSectionOpen("price")}
        onOpenChange={(open) => setSectionOpen("price", open)}
      >
        <PriceRangeSlider
          minValue={priceMin}
          maxValue={priceMax}
          absoluteMin={absoluteMin}
          absoluteMax={absoluteMax}
          onCommit={(min, max) => {
            const isDefault = min <= absoluteMin && max >= absoluteMax;
            setParams({
              min_price: isDefault ? null : min,
              max_price: isDefault ? null : max,
            });
            notify();
          }}
        />
      </AccordionFilter>

      <AccordionFilter
        title="موجودی"
        open={isSectionOpen("stock")}
        onOpenChange={(open) => setSectionOpen("stock", open)}
      >
        <Checkbox
          id="in-stock-only"
          checked={params.in_stock ?? false}
          onCheckedChange={(checked) => {
            setParams({ in_stock: checked ? "1" : null });
            notify();
          }}
          label="فقط کالاهای موجود"
          className="min-h-11"
        />
        <Checkbox
          id="on-sale-only"
          checked={params.on_sale ?? false}
          onCheckedChange={(checked) => {
            setParams({ on_sale: checked ? "1" : null });
            notify();
          }}
          label="فقط کالاهای تخفیف‌دار"
          className="min-h-11"
        />
      </AccordionFilter>

      {specOptions && Object.keys(specOptions.technical_specs).length > 0 && (
        <AccordionFilter
          title="مشخصات فنی"
          hint="بر اساس دستهٔ انتخاب‌شده"
          open={isSectionOpen("specs")}
          onOpenChange={(open) => setSectionOpen("specs", open)}
        >
          {Object.entries(specOptions.technical_specs).map(([key, values]) => (
            <SpecFilterRow
              key={key}
              specKey={key}
              values={values}
              active={params.spec_filters?.[`technical_specs.${key}`]}
              onClear={() => {
                setSpecFilter(`technical_specs.${key}`, null);
                notify();
              }}
              onSelect={(value) => {
                const path = `technical_specs.${key}`;
                const current = params.spec_filters?.[path];
                setSpecFilter(path, current === value ? null : value);
                notify();
              }}
            />
          ))}
        </AccordionFilter>
      )}
    </>
  );

  if (isSidebar) {
    // Sticky while short; when accordions grow past the fold the page/column
    // scrolls — no viewport max-height or inner overflow pane (that clipped).
    return (
      <div className="sticky top-24 z-[1] w-full space-y-3 pe-1">
        {header}
        {body}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {header}
      {body}
    </div>
  );
}

function isBooleanLike(values: string[]): boolean {
  if (values.length === 0 || values.length > 4) return false;
  const normalized = values.map((v) => v.trim().toLowerCase());
  const boolish = new Set([
    "true",
    "false",
    "yes",
    "no",
    "1",
    "0",
    "بله",
    "خیر",
    "دارد",
    "ندارد",
  ]);
  return normalized.every((v) => boolish.has(v));
}

function isNumericLooking(values: string[]): boolean {
  if (values.length === 0) return false;
  return values.every((v) => /^-?\d+([.,]\d+)?$/.test(v.trim()));
}

function SpecFilterRow({
  specKey,
  values,
  active,
  onClear,
  onSelect,
}: {
  specKey: string;
  values: string[];
  active?: string;
  onClear: () => void;
  onSelect: (value: string) => void;
}) {
  const label = useFeatureLabel(specKey);
  const [query, setQuery] = useState("");
  const booleanLike = isBooleanLike(values);
  const numericLike = !booleanLike && isNumericLooking(values) && values.length <= 8;
  const longList = !booleanLike && !numericLike && values.length > 6;

  const visible = useMemo(() => {
    if (!longList) return values;
    const q = query.trim().toLowerCase();
    if (!q) return values;
    return values.filter((v) => v.toLowerCase().includes(q));
  }, [values, query, longList]);

  const chipShowMore = useFilterShowMore(visible.length, query);

  if (booleanLike) {
    return (
      <div className="mb-4 last:mb-0">
        <p className="mb-2 text-xs font-bold text-steel">{label}</p>
        <div className="flex flex-wrap gap-2" role="group" aria-label={label}>
          {values.map((value) => {
            const on = active === value;
            return (
              <button
                key={value}
                type="button"
                aria-pressed={on}
                onClick={() => (on ? onClear() : onSelect(value))}
                className={cn(
                  "inline-flex min-h-10 items-center rounded-full px-4 text-xs font-bold transition-colors",
                  on
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:bg-muted",
                )}
              >
                {value}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  if (numericLike) {
    return (
      <div className="mb-4 last:mb-0">
        <p className="mb-2 text-xs font-bold text-steel">{label}</p>
        <div
          className="flex flex-wrap gap-1 rounded-xl bg-secondary p-1"
          role="radiogroup"
          aria-label={label}
        >
          <button
            type="button"
            role="radio"
            aria-checked={!active}
            onClick={onClear}
            className={cn(
              "min-h-10 flex-1 rounded-lg px-2 text-xs font-bold transition-colors",
              !active ? "bg-card text-foreground shadow-soft" : "text-steel hover:text-foreground",
            )}
          >
            همه
          </button>
          {values.map((value) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={active === value}
              onClick={() => onSelect(value)}
              className={cn(
                "min-h-10 flex-1 rounded-lg px-2 text-xs font-bold transition-colors tnum",
                active === value
                  ? "bg-card text-primary shadow-soft"
                  : "text-steel hover:text-foreground",
              )}
            >
              {toPersianDigits(value)}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-4 last:mb-0">
      <p className="mb-2 text-xs font-bold text-steel">{label}</p>
      {longList && (
        <div className="relative mb-2">
          <span className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            <Search size="small" set="light" />
          </span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`جستجو در ${label}…`}
            aria-label={`جستجو در ${label}`}
            className="h-11 w-full rounded-xl bg-input ps-9 pe-3 text-base outline-none focus:ring-2 focus:ring-ring/40"
          />
        </div>
      )}
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={label}>
        <button
          type="button"
          role="radio"
          aria-checked={!active}
          onClick={onClear}
          className={cn(
            "inline-flex min-h-10 items-center rounded-xl px-3 py-2 text-xs font-bold transition-colors",
            !active
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground hover:bg-muted",
          )}
        >
          همه
        </button>
        {visible.slice(0, chipShowMore.visibleCount).map((value) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active === value}
            onClick={() => onSelect(value)}
            className={cn(
              "inline-flex min-h-10 items-center rounded-xl px-3 py-2 text-xs font-bold transition-colors",
              active === value
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground hover:bg-muted",
            )}
          >
            {value}
          </button>
        ))}
        {longList && visible.length === 0 && (
          <p className="w-full px-1 py-2 text-xs text-steel">موردی یافت نشد.</p>
        )}
      </div>
      {chipShowMore.canShowMore ? (
        <FilterShowMoreButton
          remaining={chipShowMore.remaining}
          onClick={chipShowMore.showMore}
        />
      ) : null}
    </div>
  );
}

function MultiSelectRow({
  active,
  onClick,
  label,
  meta,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  meta?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "flex min-h-11 w-full items-center gap-3 rounded-xl px-2.5 py-2 text-start text-sm transition-colors",
        active ? "bg-accent font-bold text-primary" : "text-foreground/80 hover:bg-muted",
      )}
    >
      <span
        className={cn(
          "grid h-5 w-5 shrink-0 place-items-center rounded-md border-2 transition-colors",
          active ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card",
        )}
        aria-hidden
      >
        {active ? <TickSquare set="bold" size={14} primaryColor="currentColor" /> : null}
      </span>
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {meta ? (
        <span className="shrink-0 text-[11px] font-normal text-steel">{meta}</span>
      ) : null}
    </button>
  );
}

