"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useCatalogUrlSearchParams } from "@/components/catalog/catalog-url-context";
import {
  applyCatalogParamPatch,
  parsePageParam,
} from "@/lib/pagination-url";
import {
  isApiProductSort,
  type ProductListParams,
} from "@/types/product";

const SPEC_PREFIX = "spec_";

/**
 * Storefront catalog URL scheme (comma-separated, clean & shareable):
 * - brand=1,2,3     (aliases: brand_id)
 * - country=آلمان,ژاپن
 * - category=12
 * - min_price / max_price / in_stock=1 / on_sale=1 / search / sort / spec_*
 * API calls expand brand/country to repeated FastAPI query params.
 * URL `on_sale=1` maps to live API `on_sale=true` (SQL facet before pagination).
 */
export const DEFAULT_MIN_PRICE = 0;
export const DEFAULT_MAX_PRICE = 200_000_000;

/** Keys that belong to catalog filters (used by clear / active count). */
const FILTER_KEYS = [
  "category",
  "category_id",
  "category_slug",
  "brand",
  "brand_id",
  "brand_slug",
  "country",
  "min_price",
  "max_price",
  "in_stock",
  "on_sale",
  "search",
  "sort",
] as const;

export type CatalogParamPatch = Record<
  string,
  string | number | number[] | string[] | null | undefined
>;

import { parseCountryList, parseIdList } from "@/lib/catalog-url-parse";

export { parseCountryList, parseIdList } from "@/lib/catalog-url-parse";

export function encodeIdList(ids: number[]): string | null {
  return ids.length ? ids.join(",") : null;
}

export function encodeCountryList(countries: string[]): string | null {
  return countries.length ? countries.join(",") : null;
}

export function useCatalogParams() {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useCatalogUrlSearchParams();

  const num = (key: string) => {
    const v = sp.get(key);
    return v != null && v !== "" && !Number.isNaN(Number(v)) ? Number(v) : undefined;
  };

  const params = useMemo<ProductListParams>(() => {
    const sortRaw = sp.get("sort");
    const spec_filters: Record<string, string> = {};
    sp.forEach((value, key) => {
      if (key.startsWith(SPEC_PREFIX) && value) {
        spec_filters[key.slice(SPEC_PREFIX.length).replace(/__/g, ".")] = value;
      }
    });

    const brand_ids = parseIdList(sp.get("brand") ?? sp.get("brand_id"));
    const countries = parseCountryList(sp.get("country"));

    return {
      category_id: num("category") ?? num("category_id"),
      brand_ids: brand_ids.length ? brand_ids : undefined,
      search: sp.get("search") ?? undefined,
      countries: countries.length ? countries : undefined,
      min_price: num("min_price"),
      max_price: num("max_price"),
      in_stock: sp.get("in_stock") === "1" || undefined,
      on_sale: sp.get("on_sale") === "1" || undefined,
      sort: sortRaw && isApiProductSort(sortRaw) ? sortRaw : undefined,
      spec_filters: Object.keys(spec_filters).length ? spec_filters : undefined,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sp]);

  const categorySlug = sp.get("category_slug") ?? undefined;
  const brandSlug = sp.get("brand_slug") ?? undefined;

  const page = parsePageParam(sp.get("page") ?? undefined);

  const setParams = useCallback(
    (patch: CatalogParamPatch) => {
      const next = applyCatalogParamPatch(new URLSearchParams(sp.toString()), patch);
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [router, pathname, sp],
  );

  const setPage = useCallback(
    (nextPage: number) => {
      const next = new URLSearchParams(sp.toString());
      if (nextPage <= 1) next.delete("page");
      else next.set("page", String(nextPage));
      const qs = next.toString();
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [router, pathname, sp],
  );

  const setSpecFilter = useCallback(
    (path: string, value: string | null) => {
      const key = `${SPEC_PREFIX}${path.replace(/\./g, "__")}`;
      setParams({ [key]: value });
    },
    [setParams],
  );

  const toggleBrand = useCallback(
    (id: number) => {
      const current = params.brand_ids ?? [];
      const next = current.includes(id)
        ? current.filter((x) => x !== id)
        : [...current, id];
      setParams({ brand: encodeIdList(next) });
    },
    [params.brand_ids, setParams],
  );

  const toggleCountry = useCallback(
    (country: string) => {
      const current = params.countries ?? [];
      const next = current.includes(country)
        ? current.filter((x) => x !== country)
        : [...current, country];
      setParams({ country: encodeCountryList(next) });
    },
    [params.countries, setParams],
  );

  const clearAll = useCallback(() => {
    // Drop the entire query string so category/brand/spec never linger.
    router.replace(pathname.split("?")[0] || pathname, { scroll: false });
  }, [router, pathname]);

  const clearCategory = useCallback(() => {
    setParams({ category: null, roots: null });
  }, [setParams]);

  /**
   * Leave a locked category hub (`/categories/{slug}`) for free PLP filtering.
   * Preserves non-category facets when `preserveFacets` is true.
   */
  const unlockToCatalog = useCallback(
    (opts?: { preserveFacets?: boolean }) => {
      if (!opts?.preserveFacets) {
        router.replace("/catalog", { scroll: false });
        return;
      }
      const next = new URLSearchParams(sp.toString());
      next.delete("category");
      next.delete("category_id");
      next.delete("category_slug");
      next.delete("roots");
      next.delete("page");
      const qs = next.toString();
      router.replace(qs ? `/catalog?${qs}` : "/catalog", { scroll: false });
    },
    [router, sp],
  );

  /**
   * Apply category filter. On hub pages (`lockedCategoryId`), navigate to
   * `/catalog?category=<id>` so the path lock cannot overwrite L2/L3 or clear.
   */
  const applyCategory = useCallback(
    (id: number | null, opts?: { lockedCategoryId?: number | null }) => {
      const locked = opts?.lockedCategoryId;
      if (id == null) {
        if (locked != null) unlockToCatalog({ preserveFacets: true });
        else setParams({ category: null, roots: null });
        return;
      }
      if (locked != null) {
        const next = new URLSearchParams(sp.toString());
        next.delete("category_id");
        next.delete("category_slug");
        next.delete("roots");
        next.delete("page");
        next.set("category", String(id));
        router.replace(`/catalog?${next.toString()}`, { scroll: false });
        return;
      }
      setParams({ category: id, roots: null });
    },
    [unlockToCatalog, setParams, sp, router],
  );

  const activeCount = useMemo(() => {
    let n = 0;
    if (sp.get("category") || sp.get("category_id") || sp.get("category_slug")) n += 1;
    const brands = parseIdList(sp.get("brand") ?? sp.get("brand_id"));
    if (brands.length || sp.get("brand_slug")) n += brands.length || 1;
    const countries = parseCountryList(sp.get("country"));
    if (countries.length) n += countries.length;
    if (sp.get("min_price") || sp.get("max_price")) n += 1;
    if (sp.get("in_stock") === "1") n += 1;
    if (sp.get("on_sale") === "1") n += 1;
    if (sp.get("search")) n += 1;
    sp.forEach((value, key) => {
      if (key.startsWith(SPEC_PREFIX) && value) n += 1;
    });
    return n;
  }, [sp]);

  return {
    params,
    page,
    setPage,
    setParams,
    setSpecFilter,
    toggleBrand,
    toggleCountry,
    clearAll,
    clearCategory,
    unlockToCatalog,
    applyCategory,
    activeCount,
    raw: sp,
    categorySlug,
    brandSlug,
    filterKeys: FILTER_KEYS,
  };
}
