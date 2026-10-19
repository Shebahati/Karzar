import { describe, expect, it } from "vitest";
import {
  buildCuratedBestsellerProducts,
  shouldRenderCuratedBestsellersRail,
} from "@/features/home/curated-bestsellers";
import type { ProductSummary } from "@/types/product";

function p(id: number, availability = true): ProductSummary {
  return {
    id,
    sku: `SKU-${id}`,
    name: `Product ${id}`,
    thumbnail: "/t.jpg",
    base_price: "100",
    stock_status: availability ? "موجود" : "ناموجود",
    availability,
    is_original: true,
    category: null,
    brand: null,
  };
}

describe("curated bestsellers storefront contract", () => {
  it("preserves published ID order and drops unavailable products", () => {
    const ordered = buildCuratedBestsellerProducts([3, 1, 2], [p(1), p(2, false), p(3)]);
    expect(ordered.map((x) => x.id)).toEqual([3, 1]);
  });

  it("hides rail when selection is empty after load", () => {
    expect(
      shouldRenderCuratedBestsellersRail({
        selectionLoaded: true,
        selectedIds: [],
        productsLoading: false,
        visibleCount: 0,
      }),
    ).toBe(false);
  });

  it("hides rail when every published product is filtered out", () => {
    expect(
      shouldRenderCuratedBestsellersRail({
        selectionLoaded: true,
        selectedIds: [9],
        productsLoading: false,
        visibleCount: 0,
      }),
    ).toBe(false);
  });

  it("shows rail while products are loading", () => {
    expect(
      shouldRenderCuratedBestsellersRail({
        selectionLoaded: true,
        selectedIds: [1, 2],
        productsLoading: true,
        visibleCount: 0,
      }),
    ).toBe(true);
  });
});
