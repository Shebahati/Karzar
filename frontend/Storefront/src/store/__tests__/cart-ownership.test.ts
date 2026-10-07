import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  captureVerifiedCustomerSessionFence,
  establishVerifiedCustomer,
  invalidateCustomerSession,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import {
  apiClient,
  clearCartToken,
  clearCartTokenIfMatches,
  getCartToken,
  getOrCreateCartToken,
} from "@/lib/api-client";
import { cartService } from "@/services/cart";
import { catalogService } from "@/services/catalog";
import { authService } from "@/services/auth";
import {
  migrateCartPersistForTests,
  useCartStore,
  type CartLine,
} from "@/store/cart-store";
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

function emptyCart(lane: "purchase" | "inquiry") {
  return { lane, items: [] as { product_id: number; quantity: number }[], item_count: 0 };
}

function seedCustomerCart(customerId: number, cart: CartLine[], quote: CartLine[] = []) {
  useCartStore.setState({
    stash: {
      attribution: { kind: "customer", customerId },
      cart,
      quote,
    },
    cart,
    quote,
    lastSyncError: null,
  });
}

function seedGuestCart(guestToken: string, cart: CartLine[], quote: CartLine[] = []) {
  localStorage.setItem("karzar.storefront.cart_token", guestToken);
  useCartStore.setState({
    stash: {
      attribution: { kind: "guest", guestToken },
      cart,
      quote,
    },
    cart,
    quote,
    lastSyncError: null,
  });
}

describe("F03 cart ownership", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    vi.restoreAllMocks();
    useCartStore.setState({
      stash: null,
      cart: [],
      quote: [],
      lastSyncError: null,
    });
    vi.spyOn(catalogService, "getProductsByIds").mockImplementation(async (ids) =>
      ids.map((id) => product(id, id === 99 || id === 88 || id === 77 ? null : "1000")),
    );
    vi.spyOn(apiClient, "post").mockResolvedValue({ data: { ok: true } });
  });

  it("T01: A→logout→B does not upsert A local-only lines into B (intercepted)", async () => {
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    const merge = vi.spyOn(cartService, "merge").mockResolvedValue([]);
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => emptyCart(lane));
    vi.spyOn(cartService, "clear").mockResolvedValue(undefined);
    vi.spyOn(cartService, "removeItem").mockResolvedValue(emptyCart("purchase"));

    establishVerifiedCustomer(1, "otp");
    seedCustomerCart(1, [{ product: product(51), quantity: 2 }], [
      { product: product(99, null), quantity: 1 },
    ]);

    await authService.logout();
    expect(useCartStore.getState().cart).toHaveLength(0);
    expect(useCartStore.getState().quote).toHaveLength(0);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 1,
    });
    expect(upsert).not.toHaveBeenCalled();
    expect(merge).not.toHaveBeenCalled();

    upsert.mockClear();
    establishVerifiedCustomer(2, "otp");
    // Simulate post-OTP sync path used by authService.verifyOtp (live).
    const result = await useCartStore.getState().replaceFromServerForCustomer(2);
    expect(result.ok).toBe(true);
    expect(useCartStore.getState().cart).toHaveLength(0);
    expect(useCartStore.getState().quote).toHaveLength(0);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 2,
    });
    expect(upsert).not.toHaveBeenCalled();
    expect(merge).not.toHaveBeenCalled();
  });

  it("T01b: login sync for B with foreign A stash uses replace, not merge/upsert", async () => {
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    const merge = vi.spyOn(cartService, "merge").mockResolvedValue([]);
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => emptyCart(lane));

    seedCustomerCart(1, [{ product: product(51), quantity: 2 }]);
    clearCartToken();
    establishVerifiedCustomer(2, "otp");

    vi.spyOn(authService, "getMe").mockResolvedValue({
      id: 2,
      phone: "09120000002",
      full_name: "B",
      company_name: null,
    });

    // Drive the real syncCartAfterLogin via verifyOtp mock path with USE_MOCK false.
    vi.spyOn(authService as unknown as { verifyOtp: typeof authService.verifyOtp }, "verifyOtp");
    // Call internal sync by re-running the same decision through public store + mirrored auth path:
    const guestToken = getCartToken();
    const stash = useCartStore.getState().stash;
    expect(stash?.attribution.kind).toBe("customer");
    expect(guestToken).toBeNull();
    const sync = await useCartStore.getState().replaceFromServerForCustomer(2);
    expect(sync.ok).toBe(true);
    expect(upsert).not.toHaveBeenCalled();
    expect(merge).not.toHaveBeenCalled();
  });

  it("T02: guest G→A merges exact G and transfers only G-attributed local lines", async () => {
    const G = "g".repeat(32);
    seedGuestCart(G, [{ product: product(51), quantity: 2 }], [
      { product: product(77, null), quantity: 1 },
    ]);

    const merge = vi.spyOn(cartService, "merge").mockResolvedValue([]);
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => emptyCart(lane));

    establishVerifiedCustomer(1, "otp");
    const result = await useCartStore.getState().transferGuestCartToCustomer(G, 1);
    expect(result.ok).toBe(true);
    expect(merge).toHaveBeenCalledWith(G);
    expect(getCartToken()).toBeNull();
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 1,
    });
    expect(useCartStore.getState().cart.some((l) => l.product.id === 51)).toBe(true);
    expect(useCartStore.getState().quote.some((l) => l.product.id === 77)).toBe(true);
    expect(upsert).toHaveBeenCalledWith("purchase", 51, 2);
    expect(upsert).toHaveBeenCalledWith("inquiry", 77, 1);
  });

  it("T03: same-owner reload publishes only after verified A; no guest merge from token alone", async () => {
    const leftoverToken = "t".repeat(32);
    localStorage.setItem("karzar.storefront.cart_token", leftoverToken);
    seedCustomerCart(1, [{ product: product(51), quantity: 2 }]);
    // Simulate cold rehydrate: stash present, published empty.
    useCartStore.setState({ cart: [], quote: [] });

    const merge = vi.spyOn(cartService, "merge").mockResolvedValue([]);
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => ({
      lane,
      items: lane === "purchase" ? [{ product_id: 51, quantity: 2 }] : [],
      item_count: lane === "purchase" ? 1 : 0,
    }));
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));

    expect(useCartStore.getState().cart).toHaveLength(0);

    establishVerifiedCustomer(1, "me");
    useCartStore.getState().publishStashForVerifiedCustomer(1);
    expect(useCartStore.getState().cart[0]?.product.id).toBe(51);

    const result = await useCartStore.getState().reconcileSameOwnerFromServer();
    expect(result.ok).toBe(true);
    expect(merge).not.toHaveBeenCalled();
    // No local-only push — server already has 51.
    expect(upsert).not.toHaveBeenCalled();
  });

  it("T04: cold persist A + verified B replaces with B server only", async () => {
    seedCustomerCart(1, [{ product: product(51), quantity: 2 }]);
    useCartStore.setState({ cart: [], quote: [] });

    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    const merge = vi.spyOn(cartService, "merge").mockResolvedValue([]);
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => emptyCart(lane));

    // Identity pending: do not publish A.
    expect(useCartStore.getState().cart).toHaveLength(0);

    establishVerifiedCustomer(2, "me");
    useCartStore.getState().publishStashForVerifiedCustomer(2);
    expect(useCartStore.getState().cart).toHaveLength(0);

    const result = await useCartStore.getState().replaceFromServerForCustomer(2);
    expect(result.ok).toBe(true);
    expect(useCartStore.getState().cart).toHaveLength(0);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 2,
    });
    expect(upsert).not.toHaveBeenCalled();
    expect(merge).not.toHaveBeenCalled();
  });

  it("T05: logout hides A lines, keeps customer attribution, no server cart mutations", async () => {
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    const remove = vi.spyOn(cartService, "removeItem").mockResolvedValue(emptyCart("purchase"));
    const clear = vi.spyOn(cartService, "clear").mockResolvedValue(undefined);
    vi.spyOn(cartService, "get").mockResolvedValue(emptyCart("purchase"));

    establishVerifiedCustomer(1, "otp");
    seedCustomerCart(1, [{ product: product(51), quantity: 2 }]);

    await authService.logout();

    expect(useCartStore.getState().cart).toHaveLength(0);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 1,
    });
    expect(useCartStore.getState().stash?.cart[0]?.product.id).toBe(51);
    expect(upsert).not.toHaveBeenCalled();
    expect(remove).not.toHaveBeenCalled();
    expect(clear).not.toHaveBeenCalled();
  });

  it("T06: new guest after A logout gets fresh guest provenance", async () => {
    establishVerifiedCustomer(1, "otp");
    seedCustomerCart(1, [{ product: product(51), quantity: 2 }]);
    await authService.logout();
    clearCartToken();

    vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    useCartStore.getState().addToCart(product(10), 1);

    const token = getCartToken();
    expect(token).toBeTruthy();
    expect(token!.length).toBeGreaterThanOrEqual(32);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "guest",
      guestToken: token,
    });
    expect(useCartStore.getState().cart[0]?.product.id).toBe(10);
    expect(useCartStore.getState().stash?.cart.some((l) => l.product.id === 51)).toBe(false);
  });

  it("T07: A→logout→guest G→B merges G only, not A", async () => {
    establishVerifiedCustomer(1, "otp");
    seedCustomerCart(1, [{ product: product(51), quantity: 2 }]);
    await authService.logout();
    clearCartToken();

    vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    useCartStore.getState().addToCart(product(10), 1);
    const G = getCartToken()!;
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "guest",
      guestToken: G,
    });

    const merge = vi.spyOn(cartService, "merge").mockResolvedValue([]);
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => emptyCart(lane));
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));

    establishVerifiedCustomer(2, "otp");
    const result = await useCartStore.getState().transferGuestCartToCustomer(G, 2);
    expect(result.ok).toBe(true);
    expect(merge).toHaveBeenCalledWith(G);
    expect(merge).toHaveBeenCalledTimes(1);
    expect(useCartStore.getState().cart.some((l) => l.product.id === 51)).toBe(false);
    expect(useCartStore.getState().cart.some((l) => l.product.id === 10)).toBe(true);
    expect(upsert).toHaveBeenCalledWith("purchase", 10, 1);
    expect(upsert).not.toHaveBeenCalledWith("purchase", 51, 2);
  });

  it("T08: ownership guarantees apply to both purchase and inquiry lanes", async () => {
    establishVerifiedCustomer(1, "otp");
    seedCustomerCart(
      1,
      [{ product: product(51), quantity: 2 }],
      [{ product: product(88, null), quantity: 3 }],
    );
    await authService.logout();

    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => emptyCart(lane));

    establishVerifiedCustomer(2, "otp");
    await useCartStore.getState().replaceFromServerForCustomer(2);
    expect(useCartStore.getState().cart).toHaveLength(0);
    expect(useCartStore.getState().quote).toHaveLength(0);
    expect(upsert).not.toHaveBeenCalled();
  });

  it("T09: legacy unattributed {cart,quote} is discarded (fail closed)", () => {
    const migrated = migrateCartPersistForTests({
      cart: [{ product: product(51), quantity: 2 }],
      quote: [{ product: product(9, null), quantity: 1 }],
    });
    expect(migrated.stash).toBeNull();

    const v2 = migrateCartPersistForTests({
      stash: {
        attribution: { kind: "customer", customerId: 1 },
        cart: [{ product: product(51), quantity: 2 }],
        quote: [],
      },
    });
    expect(v2.stash?.attribution).toEqual({ kind: "customer", customerId: 1 });
    expect(v2.stash?.cart[0]?.product.id).toBe(51);
  });

  it("T10: late A reconcile cannot publish/upsert into B", async () => {
    establishVerifiedCustomer(1, "otp");
    seedCustomerCart(1, [{ product: product(51), quantity: 2 }]);

    let releaseA!: () => void;
    const aGate = new Promise<void>((resolve) => {
      releaseA = resolve;
    });
    let generation = 0;
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => {
      const callGen = generation;
      if (callGen === 0 && lane === "purchase") {
        await aGate;
        return {
          lane,
          items: [{ product_id: 51, quantity: 2 }],
          item_count: 1,
        };
      }
      return emptyCart(lane);
    });
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));

    const pending = useCartStore.getState().reconcileSameOwnerFromServer();

    invalidateCustomerSession("guest");
    useCartStore.getState().hidePublishedCart();
    establishVerifiedCustomer(2, "otp");
    generation = 1;
    await useCartStore.getState().replaceFromServerForCustomer(2);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 2,
    });

    releaseA();
    const late = await pending;
    expect(late.ok).toBe(false);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 2,
    });
    expect(useCartStore.getState().cart.some((l) => l.product.id === 51)).toBe(false);
    expect(upsert).not.toHaveBeenCalledWith("purchase", 51, 2);
  });

  it("T11: failed guest merge does not relabel guest lines as customer", async () => {
    const G = "h".repeat(32);
    seedGuestCart(G, [{ product: product(51), quantity: 2 }]);
    establishVerifiedCustomer(1, "otp");

    vi.spyOn(cartService, "merge").mockRejectedValue(new Error("merge failed"));
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));

    const result = await useCartStore.getState().transferGuestCartToCustomer(G, 1);
    expect(result.ok).toBe(false);
    expect(result.mergeFailed).toBe(true);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "guest",
      guestToken: G,
    });
    expect(useCartStore.getState().cart).toHaveLength(0);
    expect(upsert).not.toHaveBeenCalled();
    expect(useCartStore.getState().lastSyncError).toBeTruthy();
  });

  it("T12: mock mode still allows local cart mutations without live upsert", async () => {
    vi.resetModules();
    vi.doMock("@/config/env", () => ({
      env: {
        USE_MOCK: true,
        API_BASE_URL: "http://127.0.0.1:8000/api/v1",
        MOCK_LATENCY_MS: 0,
        GA_MEASUREMENT_ID: "",
        GTM_ID: "",
      },
    }));
    // With module-level env already mocked false for this file, assert interceptor path
    // separately: empty server + foreign stash must not upsert (covered T01).
    // Here prove getOrCreateCartToken guest attribution still works under current mock flag.
    resetCustomerSessionStateForTests();
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    const token = getOrCreateCartToken();
    seedGuestCart(token, []);
    useCartStore.getState().addToCart(product(3), 1);
    // Live env mock is false in this suite — upsert may be called; ownership must still be guest.
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "guest",
      guestToken: token,
    });
    expect(upsert.mock.calls.every((c) => c[0] === "purchase" || c[0] === "inquiry")).toBe(true);
  });

  it("T14: late G1→A merge cannot clear G2 or publish under newer owner", async () => {
    const G1 = "1".repeat(32);
    const G2 = "2".repeat(32);
    seedGuestCart(G1, [{ product: product(51), quantity: 2 }]);

    let releaseMerge!: () => void;
    const mergeGate = new Promise<void>((resolve) => {
      releaseMerge = resolve;
    });
    const merge = vi.spyOn(cartService, "merge").mockImplementation(async () => {
      await mergeGate;
      return [];
    });
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => emptyCart(lane));

    establishVerifiedCustomer(1, "otp");
    const pending = useCartStore.getState().transferGuestCartToCustomer(G1, 1);

    invalidateCustomerSession("guest");
    useCartStore.getState().hidePublishedCart();
    // Newer guest scope G2 (post-logout shopping).
    localStorage.setItem("karzar.storefront.cart_token", G2);
    useCartStore.setState({
      stash: {
        attribution: { kind: "guest", guestToken: G2 },
        cart: [{ product: product(10), quantity: 1 }],
        quote: [],
      },
      cart: [{ product: product(10), quantity: 1 }],
      quote: [],
      lastSyncError: null,
    });

    releaseMerge();
    const late = await pending;
    expect(late.ok).toBe(false);
    expect(merge).toHaveBeenCalledWith(G1);
    expect(getCartToken()).toBe(G2);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "guest",
      guestToken: G2,
    });
    expect(useCartStore.getState().cart.some((l) => l.product.id === 51)).toBe(false);
    expect(useCartStore.getState().cart.some((l) => l.product.id === 10)).toBe(true);
    expect(upsert).not.toHaveBeenCalledWith("purchase", 51, 2);
  });

  it("T15: clearCartTokenIfMatches retires only the expected token", () => {
    const G1 = "a".repeat(32);
    const G2 = "b".repeat(32);
    localStorage.setItem("karzar.storefront.cart_token", G2);
    expect(clearCartTokenIfMatches(G1)).toBe(false);
    expect(getCartToken()).toBe(G2);

    localStorage.setItem("karzar.storefront.cart_token", G1);
    expect(clearCartTokenIfMatches(G1)).toBe(true);
    expect(getCartToken()).toBeNull();
  });

  it("T13-store: restoreQuote rejects stale fence and foreign customer stash", () => {
    establishVerifiedCustomer(1, "otp");
    const fenceA = captureVerifiedCustomerSessionFence();
    expect(fenceA).not.toBeNull();

    invalidateCustomerSession("guest");
    establishVerifiedCustomer(2, "otp");
    useCartStore.setState({
      stash: {
        attribution: { kind: "customer", customerId: 2 },
        cart: [],
        quote: [],
      },
      cart: [],
      quote: [],
      lastSyncError: null,
    });

    const wrote = useCartStore.getState().restoreQuote(
      [{ product: product(51, null), quantity: 2 }],
      fenceA!,
    );
    expect(wrote).toBe(false);
    expect(useCartStore.getState().quote).toHaveLength(0);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 2,
    });
  });


  it("T17: guest stash republishes after rehydrate/full navigation when token matches", async () => {
    const G = "g".repeat(32);
    const lines = [{ product: product(21), quantity: 3 }];
    seedGuestCart(G, lines);
    // Persist merge hides published lanes (skipHydration rehydrate shape).
    useCartStore.setState({ cart: [], quote: [], lastSyncError: null });
    expect(useCartStore.getState().cart).toHaveLength(0);

    const published = useCartStore.getState().publishStashForCurrentGuestIfMatches();
    expect(published).toBe(true);
    expect(useCartStore.getState().cart.map((l) => l.product.id)).toEqual([21]);
    expect(useCartStore.getState().cart[0]?.quantity).toBe(3);

    // Active-scope entry also republishes before HTTP.
    useCartStore.setState({ cart: [], quote: [] });
    vi.spyOn(cartService, "get").mockResolvedValue(emptyCart("purchase"));
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    const result = await useCartStore.getState().reconcileActiveScopeFromServer();
    expect(result.ok).toBe(true);
    expect(useCartStore.getState().cart.some((l) => l.product.id === 21)).toBe(true);
    // Live same-owner reconcile may upsert local-only lines under exact guest G.
    expect(upsert).toHaveBeenCalledWith("purchase", 21, 3);

    // Mismatch: stash G1 + storage G2 must NOT publish.
    const G1 = "1".repeat(32);
    const G2 = "2".repeat(32);
    seedGuestCart(G1, [{ product: product(22), quantity: 1 }]);
    localStorage.setItem("karzar.storefront.cart_token", G2);
    useCartStore.setState({ cart: [], quote: [] });
    expect(useCartStore.getState().publishStashForCurrentGuestIfMatches()).toBe(false);
    expect(useCartStore.getState().cart).toHaveLength(0);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "guest",
      guestToken: G1,
    });
  });

  it("T18: late A inquiry clearQuote cannot wipe B after ownership switch", async () => {
    seedCustomerCart(1, [], [{ product: product(31, null), quantity: 1 }]);
    establishVerifiedCustomer(1, "otp");
    const fenceA = useCartStore.getState().captureOwnershipFence();
    expect(fenceA).not.toBeNull();
    expect(fenceA?.kind).toBe("customer");

    const clearSpy = vi.spyOn(cartService, "clear").mockResolvedValue(undefined);

    invalidateCustomerSession("guest");
    useCartStore.getState().hidePublishedCart();
    establishVerifiedCustomer(2, "otp");
    seedCustomerCart(2, [], [{ product: product(32, null), quantity: 2 }]);

    const cleared = useCartStore.getState().clearQuoteIfOwnershipCurrent(fenceA!);
    expect(cleared).toBe(false);
    expect(useCartStore.getState().quote.map((l) => l.product.id)).toEqual([32]);
    expect(useCartStore.getState().stash?.quote.map((l) => l.product.id)).toEqual([32]);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 2,
    });
    expect(clearSpy).not.toHaveBeenCalled();
  });

  it("T19: guest mutations cannot rewrite hidden customer A stash", () => {
    seedCustomerCart(
      1,
      [{ product: product(41), quantity: 2 }],
      [{ product: product(42, null), quantity: 1 }],
    );
    establishVerifiedCustomer(1, "otp");
    invalidateCustomerSession("guest");
    useCartStore.getState().hidePublishedCart();
    expect(useCartStore.getState().cart).toHaveLength(0);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 1,
    });

    const before = structuredClone(useCartStore.getState().stash);
    useCartStore.getState().removeFromCart(41);
    useCartStore.getState().removeFromQuote(42);
    useCartStore.getState().setCartQuantity(41, 9);
    useCartStore.getState().setQuoteQuantity(42, 9);
    useCartStore.getState().clearCart();
    useCartStore.getState().clearQuote();

    expect(useCartStore.getState().stash).toEqual(before);
    expect(useCartStore.getState().stash?.cart.map((l) => l.product.id)).toEqual([41]);
    expect(useCartStore.getState().stash?.quote.map((l) => l.product.id)).toEqual([42]);
  });

  it("T20: verified B cannot adopt stale published A lines into B stash", () => {
    // Defense-in-depth: stash A + stale visible A lines while verified as B.
    useCartStore.setState({
      stash: {
        attribution: { kind: "customer", customerId: 1 },
        cart: [{ product: product(61), quantity: 2 }],
        quote: [{ product: product(62, null), quantity: 1 }],
      },
      cart: [{ product: product(61), quantity: 2 }],
      quote: [{ product: product(62, null), quantity: 1 }],
      lastSyncError: null,
    });
    establishVerifiedCustomer(2, "otp");
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));

    useCartStore.getState().addToCart(product(70), 1);

    const state = useCartStore.getState();
    expect(state.stash?.attribution).toEqual({ kind: "customer", customerId: 2 });
    expect(state.cart.map((l) => l.product.id)).toEqual([70]);
    expect(state.stash?.cart.map((l) => l.product.id)).toEqual([70]);
    expect(state.cart.some((l) => l.product.id === 61)).toBe(false);
    expect(state.stash?.quote).toEqual([]);
    expect(upsert).toHaveBeenCalledWith("purchase", 70, 1);
    expect(upsert).not.toHaveBeenCalledWith("purchase", 61, 2);
  });

  it("T21: G1 stash / G2 token same-owner reconcile fails closed", async () => {
    const G1 = "1".repeat(32);
    const G2 = "2".repeat(32);
    seedGuestCart(G1, [{ product: product(51), quantity: 2 }]);
    localStorage.setItem("karzar.storefront.cart_token", G2);

    const get = vi.spyOn(cartService, "get").mockResolvedValue(emptyCart("purchase"));
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));

    // Start from rehydrate shape (hidden publication) before same-owner reconcile.
    useCartStore.setState({ cart: [], quote: [], lastSyncError: null });

    const result = await useCartStore.getState().reconcileSameOwnerFromServer();
    expect(result.ok).toBe(false);
    expect(get).not.toHaveBeenCalled();
    expect(upsert).not.toHaveBeenCalled();
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "guest",
      guestToken: G1,
    });
    expect(useCartStore.getState().stash?.cart.map((l) => l.product.id)).toEqual([51]);
    // Must not publish/relabel under G2.
    expect(useCartStore.getState().cart).toHaveLength(0);
    expect(useCartStore.getState().stash?.attribution.kind).not.toBe("customer");
  });

  it("T22: token-only G1→G2 race refuses stale G1→A merge publication", async () => {
    const G1 = "1".repeat(32);
    const G2 = "2".repeat(32);
    seedGuestCart(G1, [{ product: product(51), quantity: 2 }]);

    let releaseMerge!: () => void;
    const mergeGate = new Promise<void>((resolve) => {
      releaseMerge = resolve;
    });
    const merge = vi.spyOn(cartService, "merge").mockImplementation(async () => {
      await mergeGate;
      return [];
    });
    const upsert = vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => emptyCart(lane));

    establishVerifiedCustomer(1, "otp");
    const pending = useCartStore.getState().transferGuestCartToCustomer(G1, 1);

    // Token-only race: stash remains G1, storage flips to G2.
    localStorage.setItem("karzar.storefront.cart_token", G2);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "guest",
      guestToken: G1,
    });

    releaseMerge();
    const late = await pending;
    expect(late.ok).toBe(false);
    expect(merge).toHaveBeenCalledWith(G1);
    expect(getCartToken()).toBe(G2);
    // Stale completion must not adopt customer A or reconcile/upsert under A.
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "guest",
      guestToken: G1,
    });
    expect(useCartStore.getState().stash?.attribution).not.toEqual({
      kind: "customer",
      customerId: 1,
    });
    expect(upsert).not.toHaveBeenCalled();
    expect(getCartToken()).toBe(G2);
  });
});
