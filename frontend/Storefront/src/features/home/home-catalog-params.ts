import { catalogKeys } from "@/features/catalog/keys";
import type { ProductListParams } from "@/types/product";

/**
 * Single newest-product pool for the home page client sections (deals, bestsellers,
 * yesterday-most-viewed). Each rail shows at most 12 items but needs a wider pool
 * after discount filters and heuristic ranking — see HomeView useMemo helpers.
 */
export const HOME_CATALOG_PRODUCTS_PARAMS = {
  limit: 48,
  sort: "newest" as const,
} satisfies ProductListParams;

/** Stable React Query key shared by RSC prefetch and HomeView `useProducts`. */
export function homeCatalogProductsQueryKey() {
  return catalogKeys.products(HOME_CATALOG_PRODUCTS_PARAMS);
}
