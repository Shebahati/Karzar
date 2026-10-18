import { describe, expect, it } from "vitest";
import { curatePublishedBestsellers } from "@/features/home/curated-bestsellers";
import type { ProductSummary } from "@/types/product";

const product = (id: number, available = true): ProductSummary => ({
  id, sku: "X" + id, name: "Item " + id, thumbnail: "/images/test/product.jpg",
  base_price: "100", stock_status: available ? "موجود" : "ناموجود",
  availability: available, is_original: true, category: null, brand: null,
});

describe("owner curated bestsellers", () => {
  it("keeps selection order and omits unavailable/missing products", () => {
    expect(curatePublishedBestsellers([3, 1, 2, 99], [product(1), product(2, false), product(3)]).map(x => x.id)).toEqual([3, 1]);
  });
  it("never invents bestselling products from the newest list", () => {
    expect(curatePublishedBestsellers([], [product(1), product(2)])).toEqual([]);
  });
});
