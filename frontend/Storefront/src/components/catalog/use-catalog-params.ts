"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { ProductListParams, ProductSort } from "@/types/product";

const SORTS: ProductSort[] = [
  "newest",
  "price_asc",
  "price_desc",
  "discount_desc",
  "stock_first",
  "name_asc",
  "name_desc",
];

const SPEC_PREFIX = "spec_";

/**
 * Storefront catalog URL scheme (comma-separated, clean & shareable):
 * - brand=1,2,3     (aliases: brand_id)
 * - country=آلمان,ژاپن
 * - category=12
 * - min_price / max_price / in_stock=1 / search / sort / spec_*
 * API calls expand brand/country to repeated FastAPI query params.
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
  "search",
  "sort",
] as const;

export type CatalogParamPatch = Record<
  string,
  string | number | number[] | string[] | null | undefined
>;

/** Parse `1,2,3` (or a single token) into unique positive ints. */
export function parseIdList(raw: string | null): number[] {
  if (!raw) return [];
  const seen = new Set<number>();
  const out: number[] = [];
  for (const part of raw.split(",")) {
    const n = Number(part.trim());
    if (!Number.isFinite(n) || n <= 0 || seen.has(n)) continue;
    seen.add(n);
    out.push(n);
  }
  return out;
}

/** Parse comma-separated countries; trim + dedupe, preserve order. */
export function parseCountryList(raw: string | null): string[] {
  if (!raw) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const part of raw.split(",")) {
    const token = part.trim();
    if (!token || seen.has(token)) continue;
    seen.add(token);
    out.push(token);
  }
  return out;
}

export function encodeIdList(ids: number[]): string | null {
  return ids.length ? ids.join(",") : null;
}

export function encodeCountryList(countries: string[]): string | null {
  return countries.length ? countries.join(",") : null;
}

export function useCatalogParams() {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();

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
      sort: sortRaw && SORTS.includes(sortRaw as ProductSort)
        ? (sortRaw as ProductSort)
        : undefined,
      spec_filters: Object.keys(spec_filters).length ? spec_filters : undefined,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sp]);

  const categorySlug = sp.get("category_slug") ?? undefined;
  const brandSlug = sp.get("brand_slug") ?? undefined;

  const setParams = useCallback(
    (patch: CatalogParamPatch) => {
      const next = new URLSearchParams(sp.toString());
      for (const [key, value] of Object.entries(patch)) {
        if (value == null || value === "") {
          next.delete(key);
        } else if (Array.isArray(value)) {
          if (value.length === 0) next.delete(key);
          else next.set(key, value.map(String).join(","));
        } else {
          next.set(key, String(value));
        }
      }

      // Keep single canonical keys for category/brand — drop aliases.
      if ("category" in patch) {
        next.delete("category_id");
        next.delete("category_slug");
        if (patch.category == null || patch.category === "") {
          // Spec filters are category-scoped — clear when category is cleared.
          const toDelete: string[] = [];
          next.forEach((_, key) => {
            if (key.startsWith(SPEC_PREFIX)) toDelete.push(key);
          });
          toDelete.forEach((key) => next.delete(key));
        }
      }
      if ("brand" in patch) {
        next.delete("brand_id");
        next.delete("brand_slug");
      }

      const qs = next.toString();
      // replace: filter toggles must not spam browser history.
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
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
    router.replace(pathname, { scroll: false });
  }, [router, pathname]);

  const activeCount = useMemo(() => {
    let n = 0;
    if (sp.get("category") || sp.get("category_id") || sp.get("category_slug")) n += 1;
    const brands = parseIdList(sp.get("brand") ?? sp.get("brand_id"));
    if (brands.length || sp.get("brand_slug")) n += brands.length || 1;
    const countries = parseCountryList(sp.get("country"));
    if (countries.length) n += countries.length;
    if (sp.get("min_price") || sp.get("max_price")) n += 1;
    if (sp.get("in_stock") === "1") n += 1;
    if (sp.get("search")) n += 1;
    sp.forEach((value, key) => {
      if (key.startsWith(SPEC_PREFIX) && value) n += 1;
    });
    return n;
  }, [sp]);

  return {
    params,
    setParams,
    setSpecFilter,
    toggleBrand,
    toggleCountry,
    clearAll,
    activeCount,
    raw: sp,
    categorySlug,
    brandSlug,
    filterKeys: FILTER_KEYS,
  };
}
