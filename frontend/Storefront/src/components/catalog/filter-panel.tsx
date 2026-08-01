"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronRight, CloseSquare, Search, TickSquare } from "react-iconly";
import { Checkbox } from "@/components/ui/checkbox";
import { cn, formatNumber, toPersianDigits } from "@/lib/utils";
import { useBrands, useFlatCategories, useNavGroupDefs, useSpecFilterOptions } from "@/features/catalog/queries";
import { useFeatureLabel } from "@/lib/feature-labels";
import { AccordionFilter } from "@/components/catalog/accordion-filter";
import { PriceRangeSlider } from "@/components/catalog/price-range-slider";
import {
  DEFAULT_MAX_PRICE,
  DEFAULT_MIN_PRICE,
  encodeCountryList,
  useCatalogParams,
} from "@/components/catalog/use-catalog-params";
import { isTaxonomyRoot, NAV_GROUPS, sortByNavOrder, type NavGroupDef } from "@/config/nav-groups";
import type { CategoryFlat } from "@/types/category";

/** Shared filter UI rendered inside the desktop sidebar and the mobile drawer. */
export function FilterPanel({
  onApplied,
  /** When true, each change notifies parent (legacy). Prefer false + footer CTA on mobile. */
  notifyOnChange = false,
  /** Mobile drawer: open high-traffic sections so filters need fewer taps. */
  mobileDefaults = false,
}: {
  onApplied?: () => void;
  notifyOnChange?: boolean;
  mobileDefaults?: boolean;
}) {
  const {
    params,
    setParams,
    setSpecFilter,
    toggleBrand,
    toggleCountry,
    clearAll,
    activeCount,
  } = useCatalogParams();
  const { data: categories, isLoading: categoriesLoading } = useFlatCategories();
  const { data: brands, isLoading: brandsLoading } = useBrands();
  const { data: specOptions } = useSpecFilterOptions(params.category_id ?? 0);
  const { data: navDefs = NAV_GROUPS } = useNavGroupDefs();

  const [brandQuery, setBrandQuery] = useState("");
  const [categoryQuery, setCategoryQuery] = useState("");

  const notify = () => {
    if (notifyOnChange) onApplied?.();
  };

  const selectedBrandIds = params.brand_ids ?? [];
  const selectedCountries = params.countries ?? [];

  /** L1 root for the currently selected category (carousel or sidebar). */
  const scopeRootId = useMemo(() => {
    if (params.category_id == null || !categories?.length) return null;
    const byId = new Map(categories.map((c) => [c.id, c]));
    const cat = byId.get(params.category_id);
    if (!cat) return null;
    if (isTaxonomyRoot(cat)) return cat.id;
    for (const aid of cat.ancestor_ids ?? []) {
      const ancestor = byId.get(aid);
      if (ancestor && isTaxonomyRoot(ancestor)) return ancestor.id;
    }
    let current = cat;
    while (current.parent_id != null) {
      const parent = byId.get(current.parent_id);
      if (!parent) break;
      if (isTaxonomyRoot(parent)) return parent.id;
      current = parent;
    }
    return null;
  }, [params.category_id, categories]);

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

  const scopedCategories = useMemo(() => {
    const list = categories ?? [];
    if (scopeRootId == null) return list;
    return list.filter((c) => {
      if (c.id === scopeRootId) return true;
      if (c.parent_id === scopeRootId) return true;
      return (c.ancestor_ids ?? []).includes(scopeRootId);
    });
  }, [categories, scopeRootId]);

  const priceMin = params.min_price ?? DEFAULT_MIN_PRICE;
  const priceMax = params.max_price ?? DEFAULT_MAX_PRICE;
  const openBrand =
    mobileDefaults || selectedBrandIds.length > 0;
  // Category tree is a primary filter — open by default so the live tree is visible.
  const openCategory = true;
  const openCountry = selectedCountries.length > 0;
  const openPrice =
    params.min_price != null || params.max_price != null;
  const openStock = Boolean(params.in_stock);
  const openSpecs = Boolean(
    params.spec_filters && Object.keys(params.spec_filters).length > 0,
  );

  const selectedCategory = useMemo(
    () =>
      params.category_id != null
        ? (categories ?? []).find((c) => c.id === params.category_id)
        : undefined,
    [categories, params.category_id],
  );

  const categoryHint = useMemo(() => {
    if (selectedCategory?.name) return selectedCategory.name;
    if (!categoriesLoading && (categories?.length ?? 0) > 0) {
      return `${toPersianDigits(categories!.length)} دسته از سرور`;
    }
    return undefined;
  }, [selectedCategory, categoriesLoading, categories]);

  const selectCategory = (id: number | null) => {
    // Selecting a concrete node drives `category` → API `category_id`.
    // Drop legacy multi-root param whenever category changes.
    setParams({ category: id, roots: null });
    notify();
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 px-0.5">
        <h2 className="text-base font-bold tracking-tight text-foreground">فیلترها</h2>
        {activeCount > 0 && (
          <button
            type="button"
            onClick={() => {
              clearAll();
              setBrandQuery("");
              setCategoryQuery("");
              notify();
            }}
            className="inline-flex min-h-11 items-center gap-1 rounded-lg px-2 text-xs font-bold text-primary hover:bg-accent"
          >
            <CloseSquare size="small" set="light" />
            حذف همه ({formatNumber(activeCount)})
          </button>
        )}
      </div>

      <AccordionFilter
        title="دسته‌بندی"
        hint={categoryHint}
        badge={
          params.category_id != null ? toPersianDigits(1) : undefined
        }
        defaultOpen={openCategory}
      >
        <div className="relative mb-3">
          <span className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            <Search size="small" set="light" />
          </span>
          <input
            value={categoryQuery}
            onChange={(e) => setCategoryQuery(e.target.value)}
            placeholder="جستجوی دسته…"
            aria-label="جستجوی دسته‌بندی"
            className="h-11 w-full rounded-xl bg-input ps-9 pe-3 text-base outline-none focus:ring-2 focus:ring-ring/40 md:text-sm"
          />
        </div>
        <div className="max-h-80 space-y-0.5 overflow-y-auto pe-1">
          <ChipButton
            active={params.category_id == null}
            onClick={() => selectCategory(null)}
          >
            همه کالاها
          </ChipButton>
          {scopeRootId != null &&
            (() => {
              const root = (categories ?? []).find((c) => c.id === scopeRootId);
              if (!root) return null;
              return (
                <ChipButton
                  key={root.id}
                  active={params.category_id === root.id}
                  onClick={() => selectCategory(root.id)}
                >
                  {root.name}
                </ChipButton>
              );
            })()}
          {categoriesLoading ? (
            <p className="px-2 py-3 text-xs text-steel">در حال بارگذاری…</p>
          ) : (
            <CategoryAccordion
              categories={scopedCategories}
              activeId={params.category_id}
              searchQuery={categoryQuery}
              navDefs={navDefs}
              /* Selected L1 → start at L2 under that root; else full L1 tree. */
              excludeRootDepth={scopeRootId != null}
              onSelect={(id) => selectCategory(id)}
            />
          )}
        </div>
      </AccordionFilter>

      <AccordionFilter
        title="برند"
        hint={
          selectedBrandIds.length > 0
            ? `${toPersianDigits(selectedBrandIds.length)} برند انتخاب شده`
            : "می‌توانید چند برند را همزمان انتخاب کنید"
        }
        badge={selectedBrandIds.length ? toPersianDigits(selectedBrandIds.length) : undefined}
        defaultOpen={openBrand}
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
        <div className="max-h-56 space-y-0.5 overflow-y-auto pe-1" role="group" aria-label="برندها">
          {brandsLoading ? (
            <p className="px-2 py-3 text-xs text-steel">در حال بارگذاری برندها…</p>
          ) : (
            <>
              {filteredBrands.map((b) => {
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
              : "انتخاب چندتایی"
          }
          badge={
            selectedCountries.length
              ? toPersianDigits(selectedCountries.length)
              : undefined
          }
          defaultOpen={openCountry}
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
            {countries.map((country) => {
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
        </AccordionFilter>
      )}

      <AccordionFilter title="محدوده قیمت" hint="تومان" defaultOpen={openPrice}>
        <PriceRangeSlider
          minValue={priceMin}
          maxValue={priceMax}
          onCommit={(min, max) => {
            const isDefault =
              min <= DEFAULT_MIN_PRICE && max >= DEFAULT_MAX_PRICE;
            setParams({
              min_price: isDefault ? null : min,
              max_price: isDefault ? null : max,
            });
            notify();
          }}
        />
      </AccordionFilter>

      <AccordionFilter title="موجودی" defaultOpen={openStock}>
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
      </AccordionFilter>

      {specOptions && Object.keys(specOptions.technical_specs).length > 0 && (
        <AccordionFilter
          title="مشخصات فنی"
          hint="بر اساس دستهٔ انتخاب‌شده"
          defaultOpen={openSpecs}
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
            className="h-10 w-full rounded-xl bg-input ps-9 pe-3 text-sm outline-none focus:ring-2 focus:ring-ring/40"
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
        {visible.map((value) => (
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
    </div>
  );
}

function CategoryAccordion({
  categories,
  activeId,
  searchQuery,
  onSelect,
  excludeRootDepth = false,
  navDefs = NAV_GROUPS,
}: {
  categories: CategoryFlat[];
  activeId?: number;
  searchQuery: string;
  onSelect: (id: number) => void;
  /** When true, skip L1 taxonomy roots (already selected via catalog carousel). */
  excludeRootDepth?: boolean;
  navDefs?: NavGroupDef[];
}) {
  const byId = useMemo(() => new Map(categories.map((c) => [c.id, c])), [categories]);

  const childrenByParent = useMemo(() => {
    const map = new Map<number | null, CategoryFlat[]>();
    const ensure = (node: CategoryFlat) => {
      if (excludeRootDepth && isTaxonomyRoot(node)) return;
      const parent = node.parent_id ?? null;
      const list = map.get(parent) ?? [];
      if (!list.some((c) => c.id === node.id)) {
        list.push(node);
        map.set(parent, list);
      }
    };

    for (const c of categories) {
      if (excludeRootDepth && isTaxonomyRoot(c)) continue;
      // Only hide categories the API marks as empty — missing count must still show.
      const knownEmpty = c.product_count != null && c.product_count === 0;
      if (knownEmpty && c.id !== activeId) continue;
      ensure(c);
    }

    // Keep ancestors of visible / active nodes so the drill-down path stays intact.
    const seedIds = [...map.values()].flat().map((c) => c.id);
    if (activeId != null) seedIds.push(activeId);
    for (const id of seedIds) {
      let current = byId.get(id);
      while (current) {
        ensure(current);
        current =
          current.parent_id != null ? byId.get(current.parent_id) : undefined;
      }
    }

    return map;
  }, [categories, activeId, excludeRootDepth, byId]);

  const activeAncestors = useMemo(() => {
    if (activeId == null) return new Set<number>();
    const ids = new Set<number>();
    let current = byId.get(activeId);
    while (current) {
      ids.add(current.id);
      current = current.parent_id != null ? byId.get(current.parent_id) : undefined;
    }
    return ids;
  }, [byId, activeId]);

  const searchVisible = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return null as Set<number> | null;
    const matched = new Set<number>();
    for (const c of categories) {
      if (excludeRootDepth && isTaxonomyRoot(c)) continue;
      if (c.name.toLowerCase().includes(q)) matched.add(c.id);
    }
    const visible = new Set<number>(matched);
    for (const id of matched) {
      let current = byId.get(id);
      while (current?.parent_id != null) {
        const parent = byId.get(current.parent_id);
        if (parent && !(excludeRootDepth && isTaxonomyRoot(parent))) {
          visible.add(current.parent_id);
        }
        current = parent;
      }
      const stack = [id];
      while (stack.length) {
        const nodeId = stack.pop()!;
        for (const child of childrenByParent.get(nodeId) ?? []) {
          if (!visible.has(child.id)) {
            visible.add(child.id);
            stack.push(child.id);
          }
        }
      }
    }
    return visible;
  }, [categories, searchQuery, byId, childrenByParent, excludeRootDepth]);

  const searchExpandIds = useMemo(() => {
    if (!searchVisible) return new Set<number>();
    return new Set(searchVisible);
  }, [searchVisible]);

  const [expanded, setExpanded] = useState<Set<number>>(() => new Set(activeAncestors));

  useEffect(() => {
    if (activeAncestors.size === 0) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      activeAncestors.forEach((id) => next.add(id));
      return next;
    });
  }, [activeAncestors]);

  useEffect(() => {
    if (!searchQuery.trim()) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      searchExpandIds.forEach((id) => next.add(id));
      return next;
    });
  }, [searchQuery, searchExpandIds]);

  // L1 in merchandising order (same as home/carousel). When roots excluded, start at L2.
  const roots = useMemo(() => {
    if (!excludeRootDepth) {
      const top = childrenByParent.get(null) ?? [];
      return sortByNavOrder(top, navDefs).filter(
        (n) => !searchVisible || searchVisible.has(n.id),
      );
    }
    const out: CategoryFlat[] = [];
    const seen = new Set<number>();
    for (const [, list] of childrenByParent) {
      for (const node of list) {
        const parent = node.parent_id != null ? byId.get(node.parent_id) : undefined;
        const parentIsExcludedRoot = parent != null && isTaxonomyRoot(parent);
        const isOrphanNonRoot = node.parent_id == null && !isTaxonomyRoot(node);
        if (parentIsExcludedRoot || isOrphanNonRoot) {
          if (seen.has(node.id)) continue;
          if (searchVisible && !searchVisible.has(node.id)) continue;
          seen.add(node.id);
          out.push(node);
        }
      }
    }
    for (const n of childrenByParent.get(null) ?? []) {
      if (seen.has(n.id)) continue;
      if (searchVisible && !searchVisible.has(n.id)) continue;
      seen.add(n.id);
      out.push(n);
    }
    return out;
  }, [childrenByParent, excludeRootDepth, searchVisible, byId, navDefs]);

  if (searchVisible && roots.length === 0) {
    return <p className="px-2 py-3 text-xs text-steel">دسته‌ای یافت نشد.</p>;
  }

  if (roots.length === 0) {
    return (
      <p className="px-2 py-3 text-xs text-steel">
        {excludeRootDepth ? "زیر‌دسته‌ای موجود نیست." : "دسته‌ای موجود نیست."}
      </p>
    );
  }

  const renderNode = (node: CategoryFlat, depth: number) => {
    const kids = (childrenByParent.get(node.id) ?? []).filter(
      (n) => !searchVisible || searchVisible.has(n.id),
    );
    const hasKids = kids.length > 0;
    const isOpen = expanded.has(node.id) || Boolean(searchQuery.trim() && hasKids);
    const panelId = `cat-panel-${node.id}`;
    const isActive = activeId === node.id;
    const isAncestor = activeAncestors.has(node.id) && !isActive;

    return (
      <div key={node.id}>
        <div className="flex items-stretch gap-0.5">
          {hasKids ? (
            <button
              type="button"
              aria-expanded={isOpen}
              aria-controls={panelId}
              aria-label={isOpen ? `بستن ${node.name}` : `باز کردن ${node.name}`}
              onClick={() => {
                setExpanded((prev) => {
                  const next = new Set(prev);
                  if (next.has(node.id)) next.delete(node.id);
                  else next.add(node.id);
                  return next;
                });
              }}
              className="grid h-11 w-11 shrink-0 place-items-center rounded-lg text-muted-foreground hover:bg-muted"
            >
              <span
                className={cn(
                  "inline-flex transition-transform duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)]",
                  isOpen && "rotate-90",
                )}
                aria-hidden
              >
                <ChevronRight size="small" set="light" primaryColor="#5E5F5E" />
              </span>
            </button>
          ) : (
            <span className="w-11 shrink-0" aria-hidden />
          )}
          <button
            type="button"
            onClick={() => onSelect(node.id)}
            className={cn(
              "flex min-h-11 flex-1 items-center rounded-xl px-3 text-start text-sm transition-colors",
              isActive
                ? "bg-accent font-bold text-primary ring-1 ring-primary/20"
                : isAncestor
                  ? "font-semibold text-foreground/90 hover:bg-muted"
                  : "text-foreground/80 hover:bg-muted",
            )}
          >
            <span className="truncate">{node.name}</span>
          </button>
        </div>
        {hasKids && isOpen && (
          <div id={panelId} className="ms-4 border-s border-border/60 ps-1">
            {kids.map((child) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return <div className="space-y-0.5">{roots.map((r) => renderNode(r, 0))}</div>;
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

function ChipButton({
  active,
  indent = 0,
  onClick,
  children,
  className,
}: {
  active: boolean;
  indent?: number;
  onClick: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{ paddingInlineStart: `${0.75 + indent * 0.75}rem` }}
      className={cn(
        "flex min-h-11 w-full items-center gap-2 rounded-xl py-2 pe-3 text-start text-sm transition-colors",
        active
          ? "bg-accent font-bold text-primary ring-1 ring-primary/20"
          : "text-foreground/80 hover:bg-muted",
        className,
      )}
    >
      {children}
    </button>
  );
}
