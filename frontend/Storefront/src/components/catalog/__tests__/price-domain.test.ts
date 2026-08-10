import { describe, expect, it } from "vitest";
import {
  computePriceBounds,
  expandEqualPriceDomain,
  productFilterPrice,
} from "@/components/catalog/use-catalog-price-domain";

describe("catalog price domain", () => {
  it("reads selling base_price and skips inquiry nulls", () => {
    expect(productFilterPrice({ base_price: "780000" })).toBe(780_000);
    expect(productFilterPrice({ base_price: null })).toBeNull();
  });

  it("does not collapse to one expensive pad when nulls sort first", () => {
    const products = [
      { base_price: null },
      { base_price: null },
      { base_price: "420000" },
      { base_price: "3100000" },
      { base_price: "8900000" },
    ];
    // Simulate broken limit=1 price_asc (null first) + price_desc (max).
    const broken = computePriceBounds([products[0], products[4]]);
    expect(broken).toEqual({ min: 8_900_000, max: 8_900_000 });
    expect(expandEqualPriceDomain(broken!.min, broken!.max)).toEqual({
      min: 8_455_000,
      max: 9_345_000,
    });

    // Window scan across the sorted list recovers real ends.
    const bounds = computePriceBounds(products);
    expect(bounds).toEqual({ min: 420_000, max: 8_900_000 });
  });
});
