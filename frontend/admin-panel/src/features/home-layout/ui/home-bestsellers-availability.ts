import type { ProductSummary } from "@/types/product";
export function isCuratedAvailable(p: ProductSummary): boolean {
  return p.availability === true && (p.stock_status === "موجود" || p.stock_status === "in_stock");
}
