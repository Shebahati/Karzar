"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CloseSquare, Filter } from "react-iconly";
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
import { isPlpLcpIndex } from "@/lib/cwv";
import { formatNumber, toPersianDigits } from "@/lib/utils";
import { useFeatureLabel } from "@/lib/feature-labels";
import type { CategoryTreeNode } from "@/types/category";
import type { ProductListParams, ProductSummary } from "@/types/product";

const PAGE_SIZE = 24;
/** Auto-fetch next pages on scroll this many times after the first page; then show a button. */
const AUTO_LOAD_PAGES = 5;
const FILTERS_PANEL_ID = "catalog-filters-panel";

export function CatalogView({
  lockedCategoryId,
  lockedBrandId,
  initialTree = [],
}: {
  lockedCategoryId?: number;
  lockedBrandId?: number;
  /** RSC prefetch seed for root category carousel hydration. */
  initialTree?: CategoryTreeNode[];
} = {}) {
  const { params, activeCount, categorySlug, brandSlug, setParams, setSpecFilter, clearAll, raw } =
    useCatalogParams();
  /** Slug→id fills only when URL has slug without numeric id yet. */
  const [slugOverrides, setSlugOverrides] = useState<{
    category_id?: number;
    brand_ids?: number[];
  }>({});
  const [slugError, setSlugError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [accumulated, setAccumulated] = useState<ProductSummary[]>([]);
  const filterDrawerOpen = useUiStore((s) => s.filterDrawerOpen);
  const setDrawer = useUiStore((s) => s.setFilterDrawerOpen);

  // URL + locks drive the product query synchronously (no effect lag → empty PLP).
  const resolvedParams = useMemo<ProductListParams>(() => {
    const next: ProductListParams = { ...params };
    if (lockedCategoryId != null) next.category_id = lockedCategoryId;
    else if (next.category_id == null && slugOverrides.category_id != null) {
      next.category_id = slugOverrides.category_id;
    }
    if (lockedBrandId != null) next.brand_ids = [lockedBrandId];
    else if (!(next.brand_ids?.length) && slugOverrides.brand_ids?.length) {
      next.brand_ids = slugOverrides.brand_ids;
    }
    return next;
  }, [params, lockedCategoryId, lockedBrandId, slugOverrides]);

  const filterKey = useMemo(
    () =>
      JSON.stringify({
        category_id: resolvedParams.category_id ?? null,
        brand_ids: resolvedParams.brand_ids ?? [],
        countries: resolvedParams.countries ?? [],
        search: resolvedParams.search ?? null,
        min_price: resolvedParams.min_price ?? null,
        max_price: resolvedParams.max_price ?? null,
        in_stock: resolvedParams.in_stock ?? null,
        sort: resolvedParams.sort ?? null,
        spec_filters: resolvedParams.spec_filters ?? null,
      }),
    [resolvedParams],
  );

  // Migrate legacy multi-root `roots` URLs → single `category`.
  useEffect(() => {
    if (lockedCategoryId != null) return;
    const legacyRoots = parseIdList(raw.get("roots"));
    if (legacyRoots.length === 0) return;
    setParams({
      category: params.category_id ?? legacyRoots[0],
      roots: null,
    });
  }, [lockedCategoryId, raw, params.category_id, setParams]);

  useEffect(() => {
    setPage(1);
    setAccumulated([]);
  }, [filterKey]);

  useEffect(() => {
    if (lockedCategoryId == null) return;
    if (params.category_id !== lockedCategoryId) {
      setParams({ category: lockedCategoryId });
    }
  }, [lockedCategoryId, params.category_id, setParams]);

  useEffect(() => {
    if (lockedBrandId == null) return;
    const current = params.brand_ids ?? [];
    if (current.length !== 1 || current[0] !== lockedBrandId) {
      setParams({ brand: lockedBrandId });
    }
  }, [lockedBrandId, params.brand_ids, setParams]);

  useEffect(() => {
    let cancelled = false;
    async function resolveSlugs() {
      const errors: string[] = [];
      const overrides: { category_id?: number; brand_ids?: number[] } = {};
      try {
        if (categorySlug && !params.category_id && lockedCategoryId == null) {
          try {
            const cat = await catalogService.getCategoryBySlug(categorySlug);
            overrides.category_id = cat.id;
            if (!cancelled) setParams({ category: cat.id, category_slug: null });
          } catch {
            errors.push(`دسته «${categorySlug}» یافت نشد`);
          }
        }
        if (
          brandSlug &&
          !(params.brand_ids?.length) &&
          lockedBrandId == null
        ) {
          try {
            const brand = await catalogService.getBrandBySlug(brandSlug);
            overrides.brand_ids = [brand.id];
            if (!cancelled) setParams({ brand: brand.id, brand_slug: null });
          } catch {
            errors.push(`برند «${brandSlug}» یافت نشد`);
          }
        }
      } finally {
        if (!cancelled) {
          setSlugError(errors.length ? errors.join(" — ") : null);
          setSlugOverrides(overrides);
        }
      }
    }
    void resolveSlugs();
    return () => {
      cancelled = true;
    };
  }, [
    params.category_id,
    params.brand_ids,
    categorySlug,
    brandSlug,
    setParams,
    lockedCategoryId,
    lockedBrandId,
  ]);

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
    if (!data?.data || isPlaceholderData) return;
    setAccumulated((prev) => (page === 1 ? data.data : [...prev, ...data.data]));
  }, [data, page, isPlaceholderData]);

  // Prefer live page-1 data so we never flash EmptyState while accumulated is still clearing.
  const displayProducts =
    page === 1 && data?.data && !isPlaceholderData ? data.data : accumulated;
  const total = data?.meta.total_count ?? 0;
  const shown = displayProducts.length;
  const hasMore = !isPlaceholderData && shown < total;
  /** Pages already loaded beyond the first (page 1 → 0 auto-loads used). */
  const autoLoadsUsed = Math.max(0, page - 1);
  const canAutoLoad = hasMore && autoLoadsUsed < AUTO_LOAD_PAGES;
  const needsManualNext = hasMore && autoLoadsUsed >= AUTO_LOAD_PAGES;
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const showFilterSkeleton =
    (isLoading || isPlaceholderData || (isFetching && page === 1 && shown === 0)) &&
    page === 1;
  const showEmpty =
    !showFilterSkeleton && !isFetching && !isPlaceholderData && total === 0;

  const loadNextPage = useCallback(() => {
    if (isFetching || !hasMore) return;
    setPage((p) => p + 1);
  }, [hasMore, isFetching]);

  useEffect(() => {
    if (!canAutoLoad || showFilterSkeleton || shown === 0) return;
    const node = loadMoreRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) loadNextPage();
      },
      { root: null, rootMargin: "280px 0px", threshold: 0 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [canAutoLoad, loadNextPage, showFilterSkeleton, shown]);

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
    lockedBrandId == null &&
    activeCategory?.slug &&
    !params.search &&
    !selectedBrandIds.length &&
    !selectedCountries.length &&
    params.min_price == null &&
    params.max_price == null &&
    !params.in_stock;

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
      clear: () => setParams({ category: null, roots: null }),
    });
  }
  for (const brandId of selectedBrandIds) {
    const name = brands?.find((b) => b.id === brandId)?.name ?? `برند #${brandId}`;
    chips.push({
      key: `brand-${brandId}`,
      label: name,
      clear: () => {
        if (lockedBrandId != null) return;
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
        {lockedCategoryId == null ? (
          <h1 className="text-2xl font-bold text-foreground">{title}</h1>
        ) : (
          <h1 className="sr-only">{title}</h1>
        )}
        <p className={`text-sm text-muted-foreground ${lockedCategoryId == null ? "mt-1" : ""}`}>
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
              className="inline-flex min-h-11 items-center gap-1.5 rounded-md bg-accent px-3 py-2 text-xs font-medium text-accent-foreground"
            >
              {chip.label}
              <CloseSquare size={14} set="bold" primaryColor="#D02327" aria-hidden />
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

      {lockedCategoryId == null && lockedBrandId == null && (
        <div className="mb-6">
          <RootCategoryCarousel initialTree={initialTree} />
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
          ) : showEmpty ? (
            <EmptyState
              onClear={clearAll}
              hasActiveFilters={activeCount > 0}
              categoryName={activeCategoryName}
            />
          ) : (
            <>
              <div
                className={`grid grid-cols-2 gap-4 transition-opacity sm:grid-cols-3 xl:grid-cols-4 ${
                  isFetching && page > 1 ? "opacity-80" : "opacity-100"
                }`}
              >
                {displayProducts.map((p, i) => (
                  <ProductCard
                    key={p.id}
                    product={p}
                    priority={page === 1 && isPlpLcpIndex(i)}
                  />
                ))}
              </div>
              {canAutoLoad && shown > 0 ? (
                <div
                  ref={loadMoreRef}
                  className="mt-8 flex h-12 items-center justify-center"
                  aria-hidden={!isFetching}
                >
                  {isFetching ? (
                    <p className="text-sm text-muted-foreground">در حال بارگذاری…</p>
                  ) : null}
                </div>
              ) : null}
              {needsManualNext && shown > 0 ? (
                <div className="mt-8 flex justify-center">
                  <Button
                    variant="outline"
                    disabled={isFetching}
                    onClick={loadNextPage}
                  >
                    {isFetching ? "در حال بارگذاری…" : "ادامه محصولات"}
                  </Button>
                </div>
              ) : null}
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
      className="inline-flex min-h-11 items-center gap-1.5 rounded-md bg-accent px-3 py-2 text-xs font-medium text-accent-foreground"
    >
      {text}
      <CloseSquare size={14} set="bold" primaryColor="#D02327" aria-hidden />
    </button>
  );
}

function EmptyState({
  onClear,
  hasActiveFilters,
  categoryName,
}: {
  onClear: () => void;
  hasActiveFilters: boolean;
  categoryName?: string;
}) {
  const title = hasActiveFilters
    ? "با این فیلترها محصولی پیدا نشد"
    : categoryName
      ? `فعلاً محصولی در «${categoryName}» نیست`
      : "محصولی یافت نشد";
  const detail = hasActiveFilters
    ? "فیلترها را کم کنید یا همه را حذف کنید تا نتایج بیشتری ببینید."
    : categoryName
      ? "زیر‌دسته‌های مرتبط را از بالای صفحه امتحان کنید یا بعداً سر بزنید."
      : "عبارت جستجو یا فیلترها را تغییر دهید.";

  return (
    <div
      className="grid place-items-center rounded-xl bg-card py-20 text-center shadow-soft"
      dir="rtl"
      role="status"
    >
      <div className="grid h-16 w-16 place-items-center rounded-xl bg-accent text-primary">
        <Filter set="bold" primaryColor="#D02327" />
      </div>
      <p className="mt-4 font-medium text-foreground">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">{detail}</p>
      {hasActiveFilters ? (
        <Button className="mt-6" variant="outline" onClick={onClear}>
          حذف همه فیلترها
        </Button>
      ) : (
        <a
          href="/catalog"
          className="mt-6 inline-flex h-11 items-center justify-center rounded-lg px-6 text-sm font-medium text-foreground shadow-soft ring-1 ring-inset ring-border hover:bg-accent"
        >
          بازگشت به فروشگاه
        </a>
      )}
    </div>
  );
}
