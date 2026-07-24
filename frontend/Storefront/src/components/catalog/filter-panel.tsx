"use client";

import { useEffect, useMemo, useState } from "react";
import { CloseSquare, Search } from "react-iconly";
import { Checkbox } from "@/components/ui/checkbox";
import { cn, formatNumber, toPersianDigits } from "@/lib/utils";
import { useBrands, useFlatCategories, useSpecFilterOptions } from "@/features/catalog/queries";
import { useFeatureLabel } from "@/lib/feature-labels";
import { AccordionFilter } from "@/components/catalog/accordion-filter";
import { PriceRangeSlider } from "@/components/catalog/price-range-slider";
import {
  DEFAULT_MAX_PRICE,
  DEFAULT_MIN_PRICE,
  encodeCountryList,
  parseIdList,
  useCatalogParams,
} from "@/components/catalog/use-catalog-params";
import type { CategoryFlat } from "@/types/category";

/** Shared filter UI rendered inside the desktop sidebar and the mobile drawer. */
export function FilterPanel({
  onApplied,
  /** When true, each change notifies parent (legacy). Prefer false + footer CTA on mobile. */
  notifyOnChange = false,
}: {
  onApplied?: () => void;
  notifyOnChange?: boolean;
}) {
  const {
    params,
    setParams,
    setSpecFilter,
    toggleBrand,
    toggleCountry,
    clearAll,
    activeCount,
    raw,
  } = useCatalogParams();
  const { data: categories, isLoading: categoriesLoading } = useFlatCategories();
  const { data: brands, isLoading: brandsLoading } = useBrands();
  const { data: specOptions } = useSpecFilterOptions(params.category_id ?? 0);

  const [brandQuery, setBrandQuery] = useState("");
  const [categoryQuery, setCategoryQuery] = useState("");

  const notify = () => {
    if (notifyOnChange) onApplied?.();
  };

  const selectedBrandIds = params.brand_ids ?? [];
  const selectedCountries = params.countries ?? [];
  const selectedRoots = parseIdList(raw.get("roots"));

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
    if (selectedRoots.length === 0) return list;
    const rootSet = new Set(selectedRoots);
    return list.filter((c) => {
      if (rootSet.has(c.id)) return true;
      if (c.parent_id != null && rootSet.has(c.parent_id)) return true;
      return (c.ancestor_ids ?? []).some((id) => rootSet.has(id));
    });
  }, [categories, selectedRoots]);

  const priceMin = params.min_price ?? DEFAULT_MIN_PRICE;
  const priceMax = params.max_price ?? DEFAULT_MAX_PRICE;

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
        title="زیر‌دسته‌ها"
        hint={
          selectedRoots.length > 0
            ? "زیرمجموعه‌های دسته‌های انتخاب‌شده"
            : "ریشه‌ها از کاروسل بالا انتخاب می‌شوند"
        }
        defaultOpen={false}
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
            onClick={() => {
              setParams({ category: null });
              notify();
            }}
          >
            همه زیره‌ها
          </ChipButton>
          {categoriesLoading ? (
            <p className="px-2 py-3 text-xs text-steel">در حال بارگذاری…</p>
          ) : (
            <CategoryAccordion
              categories={scopedCategories}
              activeId={params.category_id}
              searchQuery={categoryQuery}
              excludeRootDepth={selectedRoots.length === 0}
              onSelect={(id) => {
                setParams({ category: id });
                notify();
              }}
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
        defaultOpen={false}
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
                  <span aria-hidden>×</span>
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
          defaultOpen={false}
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
                  <span aria-hidden>×</span>
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

      <AccordionFilter title="محدوده قیمت" hint="تومان" defaultOpen={false}>
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

      <AccordionFilter title="موجودی" defaultOpen={false}>
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
          defaultOpen={false}
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
}: {
  categories: CategoryFlat[];
  activeId?: number;
  searchQuery: string;
  onSelect: (id: number) => void;
  /** When true, skip depth-0 roots (selected via top carousel). */
  excludeRootDepth?: boolean;
}) {
  const childrenByParent = useMemo(() => {
    const map = new Map<number | null, CategoryFlat[]>();
    for (const c of categories) {
      if (excludeRootDepth && c.depth === 0) continue;
      // Hide empty categories in storefront filter nav (keep active path visible).
      if ((c.product_count ?? 0) === 0 && c.id !== activeId) continue;
      const parent = c.parent_id ?? null;
      const list = map.get(parent) ?? [];
      list.push(c);
      map.set(parent, list);
    }
    // Ensure ancestors of the active category remain visible even if count is 0.
    if (activeId != null) {
      let current = categories.find((c) => c.id === activeId);
      while (current) {
        if (!(excludeRootDepth && current.depth === 0)) {
          const parent = current.parent_id ?? null;
          const list = map.get(parent) ?? [];
          if (!list.some((c) => c.id === current!.id)) {
            list.push(current);
            map.set(parent, list);
          }
        }
        current =
          current.parent_id != null
            ? categories.find((c) => c.id === current!.parent_id)
            : undefined;
      }
    }
    return map;
  }, [categories, activeId, excludeRootDepth]);

  const byId = useMemo(() => new Map(categories.map((c) => [c.id, c])), [categories]);

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
      if (excludeRootDepth && c.depth === 0) continue;
      if (c.name.toLowerCase().includes(q)) matched.add(c.id);
    }
    const visible = new Set<number>(matched);
    for (const id of matched) {
      let current = byId.get(id);
      while (current?.parent_id != null) {
        const parent = byId.get(current.parent_id);
        if (parent && !(excludeRootDepth && parent.depth === 0)) {
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

  // When excluding depth-0, top of tree is children of roots (parent is a depth-0 id),
  // or nodes whose parent was filtered out — collect entries whose parent is missing from map.
  const roots = useMemo(() => {
    if (!excludeRootDepth) {
      return (childrenByParent.get(null) ?? []).filter(
        (n) => !searchVisible || searchVisible.has(n.id),
      );
    }
    // Depth-0 skipped: start from nodes whose parent is a root (depth 0) or null-parent non-roots.
    const out: CategoryFlat[] = [];
    const seen = new Set<number>();
    for (const [, list] of childrenByParent) {
      for (const node of list) {
        const parent = node.parent_id != null ? byId.get(node.parent_id) : undefined;
        const parentIsExcludedRoot = parent != null && parent.depth === 0;
        const isOrphanNonRoot = node.parent_id == null && node.depth !== 0;
        if (parentIsExcludedRoot || isOrphanNonRoot) {
          if (seen.has(node.id)) continue;
          if (searchVisible && !searchVisible.has(node.id)) continue;
          seen.add(node.id);
          out.push(node);
        }
      }
    }
    // Also include direct children of null that aren't depth 0 (already skipped in build).
    for (const n of childrenByParent.get(null) ?? []) {
      if (seen.has(n.id)) continue;
      if (searchVisible && !searchVisible.has(n.id)) continue;
      seen.add(n.id);
      out.push(n);
    }
    return out;
  }, [childrenByParent, excludeRootDepth, searchVisible, byId]);

  if (searchVisible && roots.length === 0) {
    return <p className="px-2 py-3 text-xs text-steel">دسته‌ای یافت نشد.</p>;
  }

  if (roots.length === 0) {
    return <p className="px-2 py-3 text-xs text-steel">زیر‌دسته‌ای موجود نیست.</p>;
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
                  "inline-block text-sm font-bold transition-transform duration-200",
                  isOpen ? "rotate-90" : "",
                )}
                aria-hidden
              >
                ›
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
        {active ? (
          <svg viewBox="0 0 12 12" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M2.5 6.5 5 9l4.5-5.5" />
          </svg>
        ) : null}
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
