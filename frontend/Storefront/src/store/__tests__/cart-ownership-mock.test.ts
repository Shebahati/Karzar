import { beforeEach, describe, expect, it, vi } from "vitest";
import { resetCustomerSessionStateForTests } from "@/lib/customer-session";
import { cartService } from "@/services/cart";
import { useCartStore } from "@/store/cart-store";
import type { ProductSummary } from "@/types/product";

vi.mock("@/config/env", () => ({
  env: {
    USE_MOCK: true,
    API_BASE_URL: "http://127.0.0.1:8000/api/v1",
    MOCK_LATENCY_MS: 0,
    GA_MEASUREMENT_ID: "",
    GTM_ID: "",
  },
}));

function product(id: number): ProductSummary {
  return {
    id,
    sku: `SKU-${id}`,
    name: `Product ${id}`,
    thumbnail: null,
    base_price: "1000",
    stock_status: "in_stock",
    availability: true,
    is_original: true,
    category: null,
    brand: null,
  };
}

describe("F03 cart ownership — mock mode (T12)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    vi.restoreAllMocks();
    useCartStore.setState({ stash: null, cart: [], quote: [], lastSyncError: null });
  });

  it("T12: USE_MOCK local cart works without requiring live cart HTTP", async () => {
    const upsert = vi.spyOn(cartService, "upsertItem");
    const get = vi.spyOn(cartService, "get");
    useCartStore.getState().addToCart(product(3), 2);
    expect(useCartStore.getState().cart[0]?.quantity).toBe(2);
    expect(useCartStore.getState().stash?.attribution.kind).toBe("guest");
    const reconcile = await useCartStore.getState().reconcileActiveScopeFromServer();
    expect(reconcile.ok).toBe(true);
    // Mock cartService short-circuits; store must not depend on network for UX.
    expect(upsert).not.toHaveBeenCalled();
    expect(get).not.toHaveBeenCalled();
  });

  it("T17: USE_MOCK republishes guest stash after rehydrate without HTTP", async () => {
    const G = "m".repeat(32);
    localStorage.setItem("karzar.storefront.cart_token", G);
    useCartStore.setState({
      stash: {
        attribution: { kind: "guest", guestToken: G },
        cart: [{ product: product(21), quantity: 3 }],
        quote: [],
      },
      cart: [],
      quote: [],
      lastSyncError: null,
    });
    const get = vi.spyOn(cartService, "get");
    const upsert = vi.spyOn(cartService, "upsertItem");
    const result = await useCartStore.getState().reconcileActiveScopeFromServer();
    expect(result.ok).toBe(true);
    expect(useCartStore.getState().cart.map((l) => l.product.id)).toEqual([21]);
    expect(get).not.toHaveBeenCalled();
    expect(upsert).not.toHaveBeenCalled();
  });
});

