import { isPubliclyAvailable } from "@/lib/public-product-availability";
import type { ProductSummary } from "@/types/product";

/** Map published IDs to storefront-visible products in display order. */
export function buildCuratedBestsellerProducts(
  selectedIds: number[],
  products: ProductSummary[] | undefined,
): ProductSummary[] {
  const byId = new Map((products ?? []).filter(isPubliclyAvailable).map((p) => [p.id, p]));
  return selectedIds.flatMap((id) => {
    const product = byId.get(id);
    return product ? [product] : [];
  });
}

/** Mirrors home-view bestsellers rail visibility (no skeleton-only hide). */
export function shouldRenderCuratedBestsellersRail(args: {
  selectionLoaded: boolean;
  selectedIds: number[];
  productsLoading: boolean;
  visibleCount: number;
}): boolean {
  if (!args.selectionLoaded) return true;
  if (args.selectedIds.length === 0) return false;
  if (!args.productsLoading && args.visibleCount === 0) return false;
  return true;
}
