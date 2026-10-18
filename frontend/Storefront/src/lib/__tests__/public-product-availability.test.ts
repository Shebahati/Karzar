import { describe, expect, it } from "vitest";
import { isPubliclyAvailable } from "@/lib/public-product-availability";
import type { ProductSummary } from "@/types/product";

function product(availability: boolean, stock_status: string): ProductSummary {
  return { id: 1, sku: "TEST", name: "Test", thumbnail: "/test.jpg",
    base_price: "100", stock_status, availability, is_original: true,
    category: null, brand: null };
}

describe("home merchandising availability", () => {
  it("only keeps explicitly available products, with matching storefront status", () => {
    expect(isPubliclyAvailable(product(true, "موجود"))).toBe(true);
    expect(isPubliclyAvailable(product(true, "in_stock"))).toBe(true);
    expect(isPubliclyAvailable(product(false, "موجود"))).toBe(false);
    expect(isPubliclyAvailable(product(true, "ناموجود"))).toBe(false);
    expect(isPubliclyAvailable(product(true, "out_of_stock"))).toBe(false);
  });
});
