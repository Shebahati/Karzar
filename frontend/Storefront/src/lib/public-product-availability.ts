import type { ProductSummary } from "@/types/product";

/** Strict storefront availability cue: disagreeing/missing flags are not promoted. */
export function isPubliclyAvailable(product: ProductSummary): boolean {
  return product.availability === true &&
    (product.stock_status === "موجود" || product.stock_status === "in_stock");
}
