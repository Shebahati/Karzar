import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  establishVerifiedCustomer,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { clearCartToken, getCartToken } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { cartService } from "@/services/cart";
import { catalogService } from "@/services/catalog";
import { authService } from "@/services/auth";
import { useCartStore } from "@/store/cart-store";
import type { ProductSummary } from "@/types/product";

vi.mock("@/config/env", () => ({
  env: {
    USE_MOCK: false,
    API_BASE_URL: "http://127.0.0.1:8000/api/v1",
    MOCK_LATENCY_MS: 0,
    GA_MEASUREMENT_ID: "",
    GTM_ID: "",
  },
}));

function product(id: number, price: string | null = "1000"): ProductSummary {
  return {
    id,
    sku: `SKU-${id}`,
    name: `Product ${id}`,
    thumbnail: null,
    base_price: price,
    stock_status: "in_stock",
    availability: true,
    is_original: true,
    category: null,
    brand: null,
  };
}

function emptyCart(lane: "purchase" | "inquiry") {
  return { lane, items: [] as { product_id: number; quantity: number }[], item_count: 0 };
}

describe("auth login cart ownership (F03 intercepted)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    vi.restoreAllMocks();
    useCartStore.setState({ stash: null, cart: [], quote: [], lastSyncError: null });
    vi.spyOn(catalogService, "getProductsByIds").mockImplementation(async (ids) =>
      ids.map((id) => product(id, id === 99 ? null : "1000")),
    );
  });

  it("T01 via verifyOtp: A local cart is not upserted into empty B", async () => {
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    const merge = vi.spyOn(cartService, "merge").mockResolvedValue([]);
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => emptyCart(lane));
    vi.spyOn(apiClient, "post").mockImplementation(async (url: string) => {
      if (url === "/auth/otp/verify") {
        return {
          data: {
            access_token: "access-b",
            refresh_token: "refresh-b",
            token_type: "bearer",
            expires_in: 1800,
            customer: { id: 2, phone: "09120000002", full_name: "User B" },
          },
        };
      }
      if (url === "/auth/logout") return { data: { ok: true } };
      throw new Error(`unexpected post ${url}`);
    });

    establishVerifiedCustomer(1, "otp");
    useCartStore.setState({
      stash: {
        attribution: { kind: "customer", customerId: 1 },
        cart: [{ product: product(51), quantity: 2 }],
        quote: [{ product: product(99, null), quantity: 1 }],
      },
      cart: [{ product: product(51), quantity: 2 }],
      quote: [{ product: product(99, null), quantity: 1 }],
      lastSyncError: null,
    });
    clearCartToken();

    await authService.logout();
    upsert.mockClear();
    merge.mockClear();

    const result = await authService.verifyOtp({ phone: "09120000002", code: "111111" });
    expect(result.customer.id).toBe(2);
    expect(result.cart_sync_error).toBeNull();
    expect(useCartStore.getState().cart).toHaveLength(0);
    expect(useCartStore.getState().quote).toHaveLength(0);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 2,
    });
    expect(merge).not.toHaveBeenCalled();
    expect(upsert).not.toHaveBeenCalled();
  });

  it("T02 via verifyOtp: guest G merges then transfers local-only lines to A", async () => {
    const G = "g".repeat(32);
    localStorage.setItem("karzar.storefront.cart_token", G);
    useCartStore.setState({
      stash: {
        attribution: { kind: "guest", guestToken: G },
        cart: [{ product: product(51), quantity: 2 }],
        quote: [],
      },
      cart: [{ product: product(51), quantity: 2 }],
      quote: [],
      lastSyncError: null,
    });

    const merge = vi.spyOn(cartService, "merge").mockResolvedValue([]);
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => emptyCart(lane));
    vi.spyOn(apiClient, "post").mockResolvedValue({
      data: {
        access_token: "access-a",
        refresh_token: "refresh-a",
        token_type: "bearer",
        expires_in: 1800,
        customer: { id: 1, phone: "09120000001", full_name: "User A" },
      },
    });

    const result = await authService.verifyOtp({ phone: "09120000001", code: "111111" });
    expect(result.customer.id).toBe(1);
    expect(merge).toHaveBeenCalledWith(G);
    expect(getCartToken()).toBeNull();
    expect(useCartStore.getState().cart.some((l) => l.product.id === 51)).toBe(true);
    expect(upsert).toHaveBeenCalledWith("purchase", 51, 2, "customer");
  });
});
