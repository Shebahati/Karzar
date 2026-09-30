import { catalogKeys } from "@/features/catalog/keys";
import type { ProductListParams } from "@/types/product";

/**
 * Newest-product pool for non-deal home rails (bestsellers, yesterday-most-viewed).
 * Deals use {@link HOME_DEALS_PRODUCTS_PARAMS} — a dedicated on_sale query.
 */
export const HOME_CATALOG_PRODUCTS_PARAMS = {
  limit: 48,
  sort: "newest" as const,
} satisfies ProductListParams;

/**
 * Home “پرتخفیف‌ها” rail — server-side discount facet.
 * Prefer in-stock discounted products for a purchasable promotional strip.
 * No silent fallback to out-of-stock rows when the set is small.
 */
export const HOME_DEALS_PRODUCTS_PARAMS = {
  on_sale: true,
  in_stock: true,
  sort: "discount_desc" as const,
  limit: 12,
} satisfies ProductListParams;

/** Stable React Query key shared by RSC prefetch and HomeView `useProducts`. */
export function homeCatalogProductsQueryKey() {
  return catalogKeys.products(HOME_CATALOG_PRODUCTS_PARAMS);
}

export function homeDealsProductsQueryKey() {
  return catalogKeys.products(HOME_DEALS_PRODUCTS_PARAMS);
}
