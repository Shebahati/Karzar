import { beforeEach, describe, expect, it } from "vitest";
import {
  selectCartCount,
  selectQuoteCount,
  useCartStore,
} from "@/store/cart-store";
import type { ProductSummary } from "@/types/product";

function product(id: number, price: string | null = "1000"): ProductSummary {
  return {
    id,
    sku: `SKU-${id}`,
    name: `محصول ${id}`,
    thumbnail: null,
    base_price: price,
    stock_status: "in_stock",
    availability: true,
    is_original: true,
    category: null,
    brand: null,
  };
}

describe("cart lanes", () => {
  beforeEach(() => {
    useCartStore.setState({ cart: [], quote: [], lastSyncError: null });
    localStorage.clear();
  });

  it("keeps purchase and inquiry lanes separate", () => {
    useCartStore.getState().addToCart(product(1, "1000"), 2);
    useCartStore.getState().addToQuote(product(2, null), 1);

    const state = useCartStore.getState();
    expect(state.cart).toHaveLength(1);
    expect(state.quote).toHaveLength(1);
    expect(selectCartCount(state)).toBe(2);
    expect(selectQuoteCount(state)).toBe(1);
  });

  it("upserts quantity in the same lane", () => {
    useCartStore.getState().addToCart(product(1), 1);
    useCartStore.getState().addToCart(product(1), 3);
    expect(useCartStore.getState().cart[0]?.quantity).toBe(4);
  });

  it("clearCart does not wipe quote", () => {
    useCartStore.getState().addToCart(product(1), 1);
    useCartStore.getState().addToQuote(product(2, null), 2);
    useCartStore.getState().clearCart();
    expect(useCartStore.getState().cart).toHaveLength(0);
    expect(selectQuoteCount(useCartStore.getState())).toBe(2);
  });
});
