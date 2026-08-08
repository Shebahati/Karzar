"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Filter } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { ProductCard, ProductCardSkeleton } from "@/components/product/product-card";
import { FilterPanel } from "@/components/catalog/filter-panel";
import { SortSelect } from "@/components/catalog/sort-select";
import { MobileFilterDrawer } from "@/components/catalog/mobile-filter-drawer";
import { RootCategoryCarousel } from "@/components/catalog/root-category-carousel";
import { parseIdList, useCatalogParams } from "@/components/catalog/use-catalog-params";
import { useFlatCategories, useProducts } from "@/features/catalog/queries";
import { catalogService } from "@/services/catalog";
import { useUiStore } from "@/store/ui-store";
import { isPlpLcpIndex } from "@/lib/cwv";
import { toPersianDigits } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";
import {
  isApiProductSort,
  type ProductListParams,
  type ProductSummary,
} from "@/types/product";

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
  const { params, activeCount, categorySlug, brandSlug, setParams, clearAll, unlockToCatalog, raw } =
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

  // URL wins over hub lock so L2/L3 drill-down and clear actually change the PLP.
  // Hub lock is only the default when the URL has no category.
  const resolvedParams = useMemo<ProductListParams>(() => {
    const next: ProductListParams = { ...params };
    if (next.category_id == null) {
      if (lockedCategoryId != null) next.category_id = lockedCategoryId;
      else if (slugOverrides.category_id != null) {
        next.category_id = slugOverrides.category_id;
      }
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
        on_sale: resolvedParams.on_sale ?? null,
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

  // Drop legacy sort keys the live API rejects (e.g. discount_desc, stock_first).
  useEffect(() => {
    const sortRaw = raw.get("sort");
    if (!sortRaw || isApiProductSort(sortRaw)) return;
    setParams({ sort: null });
  }, [raw, setParams]);

  useEffect(() => {
    setPage(1);
    setAccumulated([]);
  }, [filterKey]);

  // Do NOT force-rewrite URL back to lockedCategoryId — that made clear + L2/L3
  // selection appear broken on hub pages (selection written, then immediately overwritten).

  useEffect(() => {
    if (lockedBrandId == null) return;
    const current = params.brand_ids ?? [];
    if (current.length !== 1 || current[0] !== lockedBrandId) {
      setParams({ brand: lockedBrandId });
    }
  }, [lockedBrandId, params.brand_ids, setParams]);

  const clearAllFilters = useCallback(() => {
    if (lockedCategoryId != null) {
      unlockToCatalog({ preserveFacets: false });
      return;
    }
    clearAll();
  }, [lockedCategoryId, unlockToCatalog, clearAll]);

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
  /** Next-page fetch only — not initial PLP skeleton. */
  const isLoadingMore = isFetching && page > 1 && !showFilterSkeleton;

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
  // Keep shop H1 stable — category context lives in carousel + filter panel.
  const title = params.search
    ? `نتایج «${params.search}»`
    : "فروشگاه ابزار";

  const headerHasVisibleContent =
    lockedCategoryId == null || showFilterSkeleton || Boolean(slugError);

  return (
    <Container className="py-3 lg:py-10">
      <header
        className={
          headerHasVisibleContent ? "mb-3 lg:mb-6" : "mb-0"
        }
      >
        {lockedCategoryId == null ? (
          <h1 className="text-xl font-bold text-foreground lg:text-2xl">{title}</h1>
        ) : (
          <h1 className="sr-only">{title}</h1>
        )}
        {showFilterSkeleton ? (
          <p className={`text-sm text-muted-foreground ${lockedCategoryId == null ? "mt-1" : ""}`}>
            در حال بارگذاری…
          </p>
        ) : null}
        {slugError && (
          <p className="mt-2 text-xs text-destructive" role="status">
            {slugError}
          </p>
        )}
      </header>

      {lockedCategoryId == null && lockedBrandId == null && (
        <div className="mb-3 lg:mb-6">
          <RootCategoryCarousel initialTree={initialTree} />
        </div>
      )}

      <div className="flex gap-6">
        {/*
          Desktop filters: aside is only a width/self-start shell. Sticky +
          viewport max-height + scroll live inside FilterPanel (sidebar layout)
          so accordion expand never clips below the fold.
        */}
        <aside
          id={FILTERS_PANEL_ID}
          className="hidden w-72 shrink-0 self-start lg:block"
        >
          <FilterPanel layout="sidebar" lockedCategoryId={lockedCategoryId} />
        </aside>

        <div className="min-w-0 flex-1">
          <div className="mb-3 space-y-2.5 lg:mb-5 lg:space-y-3">
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
            <SortSelect
              totalCount={total}
              isLoading={showFilterSkeleton}
            />
          </div>

          {isError ? (
            <div className="grid place-items-center rounded-xl bg-card py-16 text-center shadow-soft">
              <p className="font-medium text-foreground">بارگذاری محصولات ناموفق بود</p>
              <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                مرتب‌سازی یا فیلتر را تغییر دهید و دوباره تلاش کنید.
              </p>
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
              onClear={clearAllFilters}
              hasActiveFilters={activeCount > 0 || lockedCategoryId != null}
              categoryName={activeCategoryName}
            />
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
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
                  className="mt-8 flex min-h-12 items-center justify-center"
                  aria-hidden={!isLoadingMore}
                >
                  <CatalogNextPageLoader active={isLoadingMore} />
                </div>
              ) : null}
              {needsManualNext && shown > 0 ? (
                <div className="mt-8 flex flex-col items-center gap-3">
                  {isLoadingMore ? <CatalogNextPageLoader active /> : null}
                  <Button
                    variant="outline"
                    disabled={isLoadingMore}
                    onClick={loadNextPage}
                  >
                    ادامه محصولات
                  </Button>
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>

      <MobileFilterDrawer
        productCount={total}
        lockedCategoryId={lockedCategoryId}
      />
    </Container>
  );
}

/** Soft footer cue while infinite-scroll / load-more appends the next page. */
function CatalogNextPageLoader({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div
      className="flex flex-col items-center gap-2.5"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <span
        className="size-[18px] animate-spin rounded-full border-[1.5px] border-primary/20 border-t-primary"
        aria-hidden
      />
      <span
        className="h-px w-10 animate-pulse rounded-full bg-primary/40"
        aria-hidden
      />
      <span className="sr-only">در حال بارگذاری محصولات بیشتر</span>
    </div>
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
