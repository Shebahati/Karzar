"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Filter } from "react-iconly";
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
import { useIsDesktopLg } from "@/lib/use-motion-safe";
import { cn, formatNumber, toPersianDigits } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";
import {
  isApiProductSort,
  type ProductListParams,
  type ProductSummary,
} from "@/types/product";

const PAGE_SIZE = 20;
/** Append batches after the initial page before switching to numbered pagination. */
const MAX_APPENDS = 2;
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
  /** How many +20 appends have been requested after the initial page. */
  const [appendCount, setAppendCount] = useState(0);
  /** Numbered pagination after MAX_APPENDS (or once the user picks a page). */
  const [usePagination, setUsePagination] = useState(false);
  /** Once true, each page replaces the grid (no more accumulating). */
  const [replaceMode, setReplaceMode] = useState(false);
  const [accumulated, setAccumulated] = useState<ProductSummary[]>([]);
  const filterDrawerOpen = useUiStore((s) => s.filterDrawerOpen);
  const setDrawer = useUiStore((s) => s.setFilterDrawerOpen);
  const isDesktop = useIsDesktopLg();
  const gridTopRef = useRef<HTMLDivElement | null>(null);
  /** Blocks double IntersectionObserver fires before `isFetching` flips. */
  const appendLockRef = useRef(false);

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

  // Filters / search / sort change → back to initial 20 + append rules.
  useEffect(() => {
    setPage(1);
    setAppendCount(0);
    setUsePagination(false);
    setReplaceMode(false);
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
    if (!data?.data || isPlaceholderData || replaceMode) return;
    setAccumulated((prev) => (page === 1 ? data.data : [...prev, ...data.data]));
    if (appendCount >= MAX_APPENDS) {
      const totalPages = Math.ceil((data.meta.total_count ?? 0) / PAGE_SIZE);
      // Only switch when more than the 3 appended pages exist.
      if (totalPages > MAX_APPENDS + 1) setUsePagination(true);
    }
  }, [data, page, isPlaceholderData, replaceMode, appendCount]);

  const total = data?.meta.total_count ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE) || 1);

  // Prefer live page-1 data so we never flash EmptyState while accumulated is still clearing.
  // After the user picks a page number, replace the grid with that page only.
  const displayProducts = replaceMode
    ? data?.data && !isPlaceholderData
      ? data.data
      : (data?.data ?? [])
    : page === 1 && data?.data && !isPlaceholderData
      ? data.data
      : accumulated;

  const shown = displayProducts.length;
  const hasMore = !isPlaceholderData && shown < total;
  const canAppend =
    !usePagination && !replaceMode && hasMore && appendCount < MAX_APPENDS;
  const showPagination = (usePagination || replaceMode) && totalPages > 1;
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const showFilterSkeleton =
    (isLoading || isPlaceholderData || (isFetching && page === 1 && shown === 0)) &&
    page === 1 &&
    !replaceMode;
  const showEmpty =
    !showFilterSkeleton && !isFetching && !isPlaceholderData && total === 0;
  /** Next-page fetch only — not initial PLP skeleton. */
  const isLoadingMore =
    isFetching && (page > 1 || replaceMode) && !showFilterSkeleton;

  useEffect(() => {
    if (!isFetching) appendLockRef.current = false;
  }, [isFetching]);

  const appendNext = useCallback(() => {
    if (isFetching || !canAppend || appendLockRef.current) return;
    appendLockRef.current = true;
    setAppendCount((c) => c + 1);
    setPage((p) => p + 1);
  }, [canAppend, isFetching]);

  const goToPage = useCallback(
    (next: number) => {
      if (next < 1 || next > totalPages || (next === page && replaceMode)) return;
      setReplaceMode(true);
      setUsePagination(true);
      setPage(next);
      gridTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    },
    [page, replaceMode, totalPages],
  );

  // Desktop: auto-append on scroll near bottom (at most MAX_APPENDS times).
  useEffect(() => {
    if (!isDesktop || !canAppend || showFilterSkeleton || shown === 0) return;
    const node = loadMoreRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) appendNext();
      },
      { root: null, rootMargin: "280px 0px", threshold: 0 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [isDesktop, canAppend, appendNext, showFilterSkeleton, shown]);

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
                  replaceMode && isLoadingMore && "opacity-60 transition-opacity duration-300",
                )}
              >
                {displayProducts.map((p, i) => (
                  <ProductCard
                    key={p.id}
                    product={p}
                    priority={!replaceMode && page === 1 && isPlpLcpIndex(i)}
                  />
                ))}
              </div>

              {/* Desktop: soft footer cue + intersection sentinel for auto-append */}
              {canAppend && isDesktop ? (
                <div
                  ref={loadMoreRef}
                  className="mt-8 flex min-h-12 items-center justify-center"
                  aria-hidden={!isLoadingMore}
                >
                  <CatalogNextPageLoader active={isLoadingMore} />
                </div>
              ) : null}

              {/* Mobile: «نمایش بیشتر» — max two appends, then pagination */}
              {canAppend && !isDesktop ? (
                <div className="mt-8 flex justify-center">
                  <button
                    type="button"
                    disabled={isLoadingMore}
                    onClick={appendNext}
                    aria-busy={isLoadingMore}
                    className={cn(
                      "inline-flex min-h-11 min-w-[10.5rem] items-center justify-center gap-2 rounded-lg px-5 text-sm font-medium text-foreground",
                      "bg-card shadow-soft ring-1 ring-inset ring-border/70",
                      "transition-[opacity,transform,background-color] duration-300",
                      "hover:bg-accent disabled:pointer-events-none",
                      isLoadingMore && "animate-pulse bg-accent/60",
                    )}
                  >
                    {isLoadingMore ? (
                      <>
                        <span
                          className="size-3.5 animate-spin rounded-full border border-primary/25 border-t-primary"
                          aria-hidden
                        />
                        <span className="text-muted-foreground">در حال بارگذاری…</span>
                      </>
                    ) : (
                      "نمایش بیشتر"
                    )}
                  </button>
                </div>
              ) : null}

              {showPagination ? (
                <CatalogPagination
                  page={page}
                  totalPages={totalPages}
                  disabled={isLoadingMore}
                  onPageChange={goToPage}
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

/** Soft footer cue while desktop infinite-scroll appends the next page. */
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

function CatalogPagination({
  page,
  totalPages,
  disabled,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  disabled?: boolean;
  onPageChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;

  const windowSize = 5;
  let start = Math.max(1, page - Math.floor(windowSize / 2));
  const end = Math.min(totalPages, start + windowSize - 1);
  start = Math.max(1, end - windowSize + 1);
  const pages = Array.from({ length: end - start + 1 }, (_, i) => start + i);

  return (
    <nav
      aria-label="صفحه‌بندی محصولات"
      className="mt-8 flex flex-wrap items-center justify-center gap-2"
    >
      <button
        type="button"
        disabled={disabled || page <= 1}
        onClick={() => onPageChange(page - 1)}
        className="inline-flex h-10 items-center gap-1 rounded-xl border border-border/60 bg-card px-3 text-xs font-bold text-[#5E5F5E] transition hover:text-[#D02327] disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronRight size="small" set="light" />
        قبلی
      </button>
      {start > 1 ? (
        <>
          <CatalogPageBtn n={1} active={page === 1} disabled={disabled} onClick={onPageChange} />
          {start > 2 ? <span className="px-1 text-[#5E5F5E]/50">…</span> : null}
        </>
      ) : null}
      {pages.map((n) => (
        <CatalogPageBtn
          key={n}
          n={n}
          active={page === n}
          disabled={disabled}
          onClick={onPageChange}
        />
      ))}
      {end < totalPages ? (
        <>
          {end < totalPages - 1 ? <span className="px-1 text-[#5E5F5E]/50">…</span> : null}
          <CatalogPageBtn
            n={totalPages}
            active={page === totalPages}
            disabled={disabled}
            onClick={onPageChange}
          />
        </>
      ) : null}
      <button
        type="button"
        disabled={disabled || page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        className="inline-flex h-10 items-center gap-1 rounded-xl border border-border/60 bg-card px-3 text-xs font-bold text-[#5E5F5E] transition hover:text-[#D02327] disabled:pointer-events-none disabled:opacity-40"
      >
        بعدی
        <ChevronLeft size="small" set="light" />
      </button>
    </nav>
  );
}

function CatalogPageBtn({
  n,
  active,
  disabled,
  onClick,
}: {
  n: number;
  active: boolean;
  disabled?: boolean;
  onClick: (page: number) => void;
}) {
  return (
    <button
      type="button"
      aria-current={active ? "page" : undefined}
      disabled={disabled}
      onClick={() => onClick(n)}
      className={cn(
        "grid h-10 min-w-10 place-items-center rounded-xl px-2.5 text-sm font-bold transition",
        active
          ? "bg-[#D02327] text-white shadow-[0_10px_24px_-14px_rgba(208,35,39,0.8)]"
          : "border border-border/60 bg-card text-[#5E5F5E] hover:text-[#D02327]",
        disabled && "pointer-events-none opacity-40",
      )}
    >
      {formatNumber(n)}
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
