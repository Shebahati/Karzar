import { CATALOG_PAGE_SIZE } from "@/config/catalog-page-size";
import { catalogListSkip } from "@/lib/pagination-url";
import type { ProductListParams } from "@/types/product";

/** Stable product list keys for React Query (RSC + client). */
export function normalizeProductListParams(
  params: ProductListParams,
): ProductListParams {
  return Object.fromEntries(
    Object.entries(params).filter(([, v]) => {
      if (v == null || v === "") return false;
      if (Array.isArray(v) && v.length === 0) return false;
      if (
        typeof v === "object" &&
        !Array.isArray(v) &&
        Object.keys(v as object).length === 0
      ) {
        return false;
      }
      return true;
    }),
  ) as ProductListParams;
}

/** PLP list params with shared page size + skip for a 1-based page index. */
export function catalogPlpParams(
  base: ProductListParams,
  page: number,
): ProductListParams {
  return normalizeProductListParams({
    ...base,
    limit: CATALOG_PAGE_SIZE,
    skip: catalogListSkip(page, CATALOG_PAGE_SIZE),
  });
}

/** Stable comparison for RSC product seeds vs client query params. */
export function productListParamsKey(params: ProductListParams): string {
  const normalized = normalizeProductListParams(params);
  const entries = Object.keys(normalized)
    .sort()
    .map((key) => [key, normalized[key as keyof ProductListParams]]);
  return JSON.stringify(entries);
}
