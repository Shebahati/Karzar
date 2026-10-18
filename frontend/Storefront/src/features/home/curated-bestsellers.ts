import { hasPublicProductImage } from "@/lib/product-image";
import type { ProductSummary } from "@/types/product";

/** The owner picks the exact product IDs and order, not a guessed sales rank. */
export function curatePublishedBestsellers(ids: number[], candidates: ProductSummary[]): ProductSummary[] {
  const byId = new Map(candidates.map((p) => [p.id, p]));
  return ids
    .map((id) => byId.get(id))
    .filter((p): p is ProductSummary =>
      Boolean(p && p.availability === true &&
        (p.stock_status === "موجود" || p.stock_status === "in_stock") &&
        hasPublicProductImage(p)));
}
