"use client";

import { useEffect, useMemo, useState } from "react";
import { Filter } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { ProductCard, ProductCardSkeleton } from "@/components/product/product-card";
import { FilterPanel } from "@/components/catalog/filter-panel";
import { SortSelect } from "@/components/catalog/sort-select";
import { MobileFilterDrawer } from "@/components/catalog/mobile-filter-drawer";
import { RootCategoryCarousel } from "@/components/catalog/root-category-carousel";
import { parseIdList, useCatalogParams } from "@/components/catalog/use-catalog-params";
import { useBrands, useFlatCategories, useProducts } from "@/features/catalog/queries";
import { catalogService } from "@/services/catalog";
import { useUiStore } from "@/store/ui-store";
import { formatNumber, toPersianDigits } from "@/lib/utils";
import { useFeatureLabel } from "@/lib/feature-labels";
import type { ProductListParams, ProductSummary } from "@/types/product";
import type { CategoryFlat } from "@/types/category";

const PAGE_SIZE = 24;
const FILTERS_PANEL_ID = "catalog-filters-panel";

function productMatchesRoots(
  product: ProductSummary,
  rootIds: number[],
  categories: CategoryFlat[] | undefined,
): boolean {
  if (rootIds.length === 0) return true;
  const rootSet = new Set(rootIds);
  const cat = product.category;
  if (!cat) return false;
  if (rootSet.has(cat.id)) return true;
  const ancestors = cat.ancestor_ids;
  if (ancestors?.some((id) => rootSet.has(id))) return true;
  // Fallback: look up flat category when product payload lacks ancestor_ids.
  const flat = categories?.find((c) => c.id === cat.id);
  if (!flat) return false;
  if (rootSet.has(flat.id)) return true;
  if (flat.parent_id != null && rootSet.has(flat.parent_id)) return true;
  return (flat.ancestor_ids ?? []).some((id) => rootSet.has(id));
}

export function CatalogView({ lockedCategoryId }: { lockedCategoryId?: number } = {}) {
  const { params, activeCount, categorySlug, brandSlug, setParams, setSpecFilter, clearAll, raw } =
    useCatalogParams();
  const selectedRoots = useMemo(() => parseIdList(raw.get("roots")), [raw]);
  const [resolvedParams, setResolvedParams] = useState<ProductListParams>(params);
  const [slugError, setSlugError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [accumulated, setAccumulated] = useState<ProductSummary[]>([]);
  const filterDrawerOpen = useUiStore((s) => s.filterDrawerOpen);
  const setDrawer = useUiStore((s) => s.setFilterDrawerOpen);

  /** Multi-root OR filter with no leaf category → client-side product filter. */
  const multiRootClientFilter =
    lockedCategoryId == null &&
    selectedRoots.length > 1 &&
    params.category_id == null;

  useEffect(() => {
    setPage(1);
    setAccumulated([]);
  }, [resolvedParams, multiRootClientFilter, selectedRoots]);

  useEffect(() => {
    if (lockedCategoryId == null) return;
    if (params.category_id !== lockedCategoryId) {
      setParams({ category: lockedCategoryId });
    }
  }, [lockedCategoryId, params.category_id, setParams]);

  useEffect(() => {
    let cancelled = false;
    async function resolveSlugs() {
      const next: ProductListParams = {
        ...params,
        ...(lockedCategoryId != null ? { category_id: lockedCategoryId } : {}),
      };
      const errors: string[] = [];
      try {
        if (categorySlug && !params.category_id && lockedCategoryId == null) {
          try {
            const cat = await catalogService.getCategoryBySlug(categorySlug);
            next.category_id = cat.id;
            if (!cancelled) setParams({ category: cat.id, category_slug: null });
          } catch {
            errors.push(`دسته «${categorySlug}» یافت نشد`);
          }
        }
        if (brandSlug && !(params.brand_ids?.length)) {
          try {
            const brand = await catalogService.getBrandBySlug(brandSlug);
            next.brand_ids = [brand.id];
            if (!cancelled) setParams({ brand: brand.id, brand_slug: null });
          } catch {
            errors.push(`برند «${brandSlug}» یافت نشد`);
          }
        }

        // Roots without a leaf category: single root → category_id; multiple → leave unset.
        if (
          lockedCategoryId == null &&
          !next.category_id &&
          !categorySlug &&
          selectedRoots.length === 1
        ) {
          next.category_id = selectedRoots[0];
        }
        if (
          lockedCategoryId == null &&
          selectedRoots.length > 1 &&
          params.category_id == null
        ) {
          next.category_id = undefined;
        }
      } finally {
        if (!cancelled) {
          setSlugError(errors.length ? errors.join(" — ") : null);
          setResolvedParams(next);
        }
      }
    }
    void resolveSlugs();
    return () => {
      cancelled = true;
    };
  }, [params, categorySlug, brandSlug, setParams, lockedCategoryId, selectedRoots]);

  const queryParams = useMemo(
    () => ({
      ...resolvedParams,
      limit: PAGE_SIZE,
      skip: (page - 1) * PAGE_SIZE,
    }),
    [resolvedParams, page],
  );
  const { data, isLoading, isFetching, isPlaceholderData, isError, refetch } =
    useProducts(queryParams);
  const { data: categories } = useFlatCategories();
  const { data: brands } = useBrands();

  useEffect(() => {
    if (!data?.data) return;
    setAccumulated((prev) => (page === 1 ? data.data : [...prev, ...data.data]));
  }, [data, page]);

  const displayProducts = useMemo(() => {
    if (!multiRootClientFilter) return accumulated;
    return accumulated.filter((p) =>
      productMatchesRoots(p, selectedRoots, categories),
    );
  }, [accumulated, multiRootClientFilter, selectedRoots, categories]);

  const total = multiRootClientFilter
    ? displayProducts.length
    : (data?.meta.total_count ?? 0);
  const shown = displayProducts.length;
  const hasMore = multiRootClientFilter
    ? (data?.meta.total_count ?? 0) > accumulated.length
    : shown < (data?.meta.total_count ?? 0);
  const activeCategory = resolvedParams.category_id
    ? categories?.find((c) => c.id === resolvedParams.category_id)
    : undefined;
  const activeCategoryName = activeCategory?.name;
  const selectedBrandIds = resolvedParams.brand_ids ?? [];
  const selectedCountries = params.countries ?? [];
  const activeBrandName =
    selectedBrandIds.length === 1
      ? brands?.find((b) => b.id === selectedBrandIds[0])?.name
      : selectedBrandIds.length > 1
        ? `${selectedBrandIds.length} برند`
        : undefined;
  const title = params.search
    ? `نتایج «${params.search}»`
    : activeCategoryName ?? activeBrandName ?? "فروشگاه ابزار";
  const onlyCategoryFilter =
    lockedCategoryId == null &&
    activeCategory?.slug &&
    !params.search &&
    !selectedBrandIds.length &&
    !selectedCountries.length &&
    params.min_price == null &&
    params.max_price == null &&
    !params.in_stock;
  const showFilterSkeleton = (isLoading || isPlaceholderData) && page === 1;

  const chips: { key: string; label: string; clear: () => void }[] = [];
  if (params.search) {
    chips.push({
      key: "search",
      label: `جستجو: ${params.search}`,
      clear: () => setParams({ search: null }),
    });
  }
  if (resolvedParams.category_id != null) {
    chips.push({
      key: "category",
      label: activeCategoryName ?? `دسته #${resolvedParams.category_id}`,
      clear: () => setParams({ category: null }),
    });
  }
  for (const brandId of selectedBrandIds) {
    const name = brands?.find((b) => b.id === brandId)?.name ?? `برند #${brandId}`;
    chips.push({
      key: `brand-${brandId}`,
      label: name,
      clear: () => {
        const next = selectedBrandIds.filter((id) => id !== brandId);
        setParams({ brand: next.length ? next.join(",") : null });
      },
    });
  }
  for (const country of selectedCountries) {
    const countryValid = !brands || brands.some((b) => b.country === country);
    if (!countryValid) continue;
    chips.push({
      key: `country-${country}`,
      label: country,
      clear: () => {
        const next = selectedCountries.filter((c) => c !== country);
        setParams({ country: next.length ? next.join(",") : null });
      },
    });
  }
  if (params.in_stock) {
    chips.push({
      key: "stock",
      label: "فقط موجود",
      clear: () => setParams({ in_stock: null }),
    });
  }
  if (params.min_price != null || params.max_price != null) {
    const minLabel =
      params.min_price != null ? formatNumber(params.min_price) : "…";
    const maxLabel =
      params.max_price != null ? formatNumber(params.max_price) : "…";
    chips.push({
      key: "price",
      label: `قیمت ${minLabel} تا ${maxLabel}`,
      clear: () => setParams({ min_price: null, max_price: null }),
    });
  }

  const specEntries = params.spec_filters
    ? Object.entries(params.spec_filters)
    : [];

  return (
    <Container className="py-6 lg:py-10">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {showFilterSkeleton
            ? "در حال بارگذاری…"
            : `${formatNumber(total)} محصول یافت شد`}
        </p>
        {onlyCategoryFilter && activeCategory?.slug ? (
          <p className="mt-2 text-xs">
            <a
              href={`/categories/${activeCategory.slug}`}
              className="font-bold text-primary hover:underline"
            >
              صفحهٔ اختصاصی این دسته
            </a>
          </p>
        ) : null}
        {slugError && (
          <p className="mt-2 text-xs text-destructive" role="status">
            {slugError}
          </p>
        )}
      </header>

      {(chips.length > 0 || specEntries.length > 0) && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {chips.map((chip) => (
            <button
              key={chip.key}
              type="button"
              onClick={chip.clear}
              aria-label={`حذف فیلتر ${chip.label}`}
              className="inline-flex min-h-11 items-center rounded-md bg-accent px-3 py-2 text-xs font-medium text-accent-foreground"
            >
              {chip.label} ×
            </button>
          ))}
          {specEntries.map(([path, value]) => (
            <SpecChip
              key={`spec:${path}`}
              path={path}
              value={value}
              onClear={() => setSpecFilter(path, null)}
            />
          ))}
          <button
            type="button"
            onClick={clearAll}
            className="inline-flex min-h-11 items-center text-xs font-medium text-primary"
          >
            حذف همه فیلترها
          </button>
        </div>
      )}

      {lockedCategoryId == null && (
        <div className="mb-6">
          <RootCategoryCarousel />
        </div>
      )}

      <div className="flex gap-6">
        <aside className="hidden w-72 shrink-0 lg:block" id={FILTERS_PANEL_ID}>
          <div className="sticky top-32">
            <FilterPanel />
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <div className="mb-5 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setDrawer(true)}
              aria-expanded={filterDrawerOpen}
              aria-controls="mobile-filter-drawer"
              className="flex min-h-11 items-center gap-2 rounded-lg bg-card px-4 py-2.5 text-sm font-medium text-foreground shadow-soft lg:hidden"
            >
              <Filter size="small" set="bold" />
              فیلترها
              {activeCount > 0 && (
                <span className="grid h-5 min-w-5 place-items-center rounded-full bg-primary px-1 text-xs text-primary-foreground tnum">
                  {toPersianDigits(String(activeCount))}
                </span>
              )}
            </button>
            <span className="hidden text-sm text-muted-foreground lg:block">مرتب‌سازی بر اساس</span>
            <div className="ms-auto">
              <SortSelect />
            </div>
          </div>

          {isError ? (
            <div className="grid place-items-center rounded-xl bg-card py-16 text-center shadow-soft">
              <p className="font-medium text-foreground">بارگذاری محصولات ناموفق بود</p>
              <Button className="mt-4" onClick={() => void refetch()}>
                تلاش مجدد
              </Button>
            </div>
          ) : showFilterSkeleton ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <ProductCardSkeleton key={i} />
              ))}
            </div>
          ) : total === 0 ? (
            <EmptyState onClear={clearAll} />
          ) : (
            <>
              <div
                className={`grid grid-cols-2 gap-4 transition-opacity sm:grid-cols-3 xl:grid-cols-4 ${
                  isFetching && page > 1 ? "opacity-80" : "opacity-100"
                }`}
              >
                {displayProducts.map((p) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
              {hasMore && (
                <div className="mt-8 flex justify-center">
                  <Button
                    variant="outline"
                    disabled={isFetching}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    {isFetching
                      ? "در حال بارگذاری…"
                    : `بارگذاری بیشتر (${formatNumber(shown)} از ${formatNumber(total)})`}
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <MobileFilterDrawer productCount={total} />
    </Container>
  );
}

function SpecChip({
  path,
  value,
  onClear,
}: {
  path: string;
  value: string;
  onClear: () => void;
}) {
  const keyName = path.includes(".") ? path.split(".").pop()! : path;
  const label = useFeatureLabel(keyName);
  const text = `${label}: ${value}`;
  return (
    <button
      type="button"
      onClick={onClear}
      aria-label={`حذف فیلتر ${text}`}
      className="inline-flex min-h-11 items-center rounded-md bg-accent px-3 py-2 text-xs font-medium text-accent-foreground"
    >
      {text} ×
    </button>
  );
}

function EmptyState({ onClear }: { onClear: () => void }) {
  return (
    <div className="grid place-items-center rounded-xl bg-card py-20 text-center shadow-soft">
      <div className="grid h-16 w-16 place-items-center rounded-xl bg-accent text-primary">
        <Filter set="bold" primaryColor="#C22026" />
      </div>
      <p className="mt-4 font-medium text-foreground">محصولی یافت نشد</p>
      <p className="mt-1 text-sm text-muted-foreground">
        فیلترها را تغییر دهید یا همه را حذف کنید.
      </p>
      <Button className="mt-6" variant="outline" onClick={onClear}>
        حذف همه فیلترها
      </Button>
    </div>
  );
}
