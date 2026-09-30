"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Filter } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { ProductCard, ProductCardSkeleton } from "@/components/product/product-card";
import { FilterPanel } from "@/components/catalog/filter-panel";
import { SortSelect } from "@/components/catalog/sort-select";
import { MobileFilterDrawer } from "@/components/catalog/mobile-filter-drawer";
import { RootCategoryCarousel } from "@/components/catalog/root-category-carousel";
import { CatalogUrlProvider } from "@/components/catalog/catalog-url-context";
import { parseIdList, useCatalogParams } from "@/components/catalog/use-catalog-params";
import { searchParamsToUrlSearchParams } from "@/lib/pagination-request";
import { useFlatCategories, useProducts } from "@/features/catalog/queries";
import { catalogService } from "@/services/catalog";
import { useUiStore } from "@/store/ui-store";
import { isPlpLcpIndex } from "@/lib/cwv";
import { CATALOG_PAGE_SIZE } from "@/config/catalog-page-size";
import { buildPaginatedHref } from "@/lib/pagination-url";
import { PaginationNav } from "@/components/ui/pagination-nav";
import { cn, toPersianDigits } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";
import { productListParamsKey } from "@/lib/catalog-plp";
import {
  isApiProductSort,
  type ProductListParams,
  type ProductListResponse,
} from "@/types/product";

const FILTERS_PANEL_ID = "catalog-filters-panel";

export type CatalogProductsSeed = {
  params: ProductListParams;
  response: ProductListResponse;
};

type ServerSearchParams = Record<string, string | string[] | undefined>;

export function CatalogView({
  lockedCategoryId,
  lockedBrandId,
  initialTree = [],
  initialProductsSeed,
  serverSearchParams = {},
}: {
  lockedCategoryId?: number;
  lockedBrandId?: number;
  /** RSC prefetch seed for root category carousel hydration. */
  initialTree?: CategoryTreeNode[];
  /** Server-fetched PLP page so raw HTML includes product anchors. */
  initialProductsSeed?: CatalogProductsSeed;
  /** Passed from RSC so PLP SSR does not suspend on useSearchParams. */
  serverSearchParams?: ServerSearchParams;
} = {}) {
  const urlSearchParams = useMemo(
    () => searchParamsToUrlSearchParams(serverSearchParams),
    [serverSearchParams],
  );

  return (
    <CatalogUrlProvider value={urlSearchParams}>
      <CatalogViewBody
        lockedCategoryId={lockedCategoryId}
        lockedBrandId={lockedBrandId}
        initialTree={initialTree}
        initialProductsSeed={initialProductsSeed}
      />
    </CatalogUrlProvider>
  );
}

function CatalogViewBody({
  lockedCategoryId,
  lockedBrandId,
  initialTree = [],
  initialProductsSeed,
}: {
  lockedCategoryId?: number;
  lockedBrandId?: number;
  initialTree?: CategoryTreeNode[];
  initialProductsSeed?: CatalogProductsSeed;
}) {
  const pathname = usePathname();
  const {
    params,
    page,
    setPage,
    activeCount,
    categorySlug,
    brandSlug,
    setParams,
    clearAll,
    unlockToCatalog,
    raw,
  } = useCatalogParams();
  /** Slug→id fills only when URL has slug without numeric id yet. */
  const [slugOverrides, setSlugOverrides] = useState<{
    category_id?: number;
    brand_ids?: number[];
  }>({});
  const [slugError, setSlugError] = useState<string | null>(null);
  const filterDrawerOpen = useUiStore((s) => s.filterDrawerOpen);
  const setDrawer = useUiStore((s) => s.setFilterDrawerOpen);
  const gridTopRef = useRef<HTMLDivElement | null>(null);

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
      limit: CATALOG_PAGE_SIZE,
      skip: (page - 1) * CATALOG_PAGE_SIZE,
    }),
    [resolvedParams, page],
  );
  const productsInitialData = useMemo(() => {
    if (!initialProductsSeed) return undefined;
    return productListParamsKey(queryParams) ===
      productListParamsKey(initialProductsSeed.params)
      ? initialProductsSeed.response
      : undefined;
  }, [initialProductsSeed, queryParams]);
  const { data, isLoading, isFetching, isPlaceholderData, isError, refetch } =
    useProducts(queryParams, productsInitialData);
  const { data: categories } = useFlatCategories();

  const resolvedPage =
    data ?? productsInitialData ?? initialProductsSeed?.response;
  const total = resolvedPage?.meta.total_count ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / CATALOG_PAGE_SIZE) || 1);

  const displayProducts =
    data?.data && !isPlaceholderData
      ? data.data
      : (productsInitialData ?? initialProductsSeed?.response)?.data ?? [];

  const visibleProducts = displayProducts;
  const shown = visibleProducts.length;
  const showPagination = totalPages > 1;
  const showFilterSkeleton =
    initialProductsSeed == null &&
    (isLoading || isPlaceholderData || (isFetching && shown === 0)) &&
    !data?.data;
  const showEmpty =
    !showFilterSkeleton && !isFetching && !isPlaceholderData && total === 0;
  const isLoadingMore = isFetching && !showFilterSkeleton && shown > 0;

  const hrefForPage = useCallback(
    (target: number) => buildPaginatedHref(pathname, raw, target),
    [pathname, raw],
  );

  const activeCategory = resolvedParams.category_id
    ? categories?.find((c) => c.id === resolvedParams.category_id)
    : undefined;
  const activeCategoryName = activeCategory?.name;
  // Keep shop H1 stable — category context lives in carousel + filter panel.
  const title = params.search
    ? `نتایج «${params.search}»`
    : "فروشگاه";

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
          Desktop filters: aside is only a width/self-start shell. Sticky lives
          inside FilterPanel (sidebar layout); tall accordion stacks scroll with
          the page — no inner max-height clip.
        */}
        <aside
          id={FILTERS_PANEL_ID}
          className="hidden w-72 shrink-0 self-start lg:block"
        >
          <FilterPanel
            layout="sidebar"
            lockedCategoryId={lockedCategoryId}
            priceSeedProducts={displayProducts}
          />
        </aside>

        <div className="min-w-0 flex-1">
          <div className="mb-3 lg:mb-5">
            <SortSelect
              totalCount={total}
              isLoading={showFilterSkeleton}
              mobileLeading={
                <button
                  type="button"
                  onClick={() => setDrawer(true)}
                  aria-expanded={filterDrawerOpen}
                  aria-controls="mobile-filter-drawer"
                  className="flex min-h-11 shrink-0 items-center gap-2 rounded-lg bg-card px-4 py-2.5 text-sm font-medium text-foreground shadow-soft"
                >
                  <Filter size="small" set="bold" />
                  فیلترها
                  {activeCount > 0 && (
                    <span className="grid h-5 min-w-5 place-items-center rounded-full bg-primary px-1 text-xs text-primary-foreground tnum">
                      {toPersianDigits(String(activeCount))}
                    </span>
                  )}
                </button>
              }
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
              <div
                ref={gridTopRef}
                className={cn(
                  "grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4",
                  isLoadingMore && "opacity-60 transition-opacity duration-300",
                )}
              >
                {visibleProducts.map((p, i) => (
                  <ProductCard
                    key={p.id}
                    product={p}
                    priority={page === 1 && isPlpLcpIndex(i)}
                  />
                ))}
              </div>

              {showPagination ? (
                <PaginationNav
                  page={page}
                  totalPages={totalPages}
                  hrefForPage={hrefForPage}
                  ariaLabel="صفحه‌بندی محصولات"
                />
              ) : null}
            </>
          )}
        </div>
      </div>

      <MobileFilterDrawer
        productCount={total}
        lockedCategoryId={lockedCategoryId}
        priceSeedProducts={displayProducts}
      />
    </Container>
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
