"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ProductSummary } from "@/types/product";
import { cartService, type CartItemResponse, type CartLane } from "@/services/cart";
import { env } from "@/config/env";
import {
  captureVerifiedCustomerSessionFence,
  getCustomerSessionSnapshot,
  getVerifiedCustomerId,
  isCustomerSessionFenceCurrent,
  type CustomerSessionFence,
} from "@/lib/customer-session";
import {
  clearCartTokenIfMatches,
  getCartToken,
  getOrCreateCartToken,
} from "@/lib/api-client";

export interface CartLine {
  product: ProductSummary;
  quantity: number;
}

/** Explicit cart provenance — never infer from token presence alone. */
export type CartAttribution =
  | { kind: "guest"; guestToken: string }
  | { kind: "customer"; customerId: number };

export type CartStash = {
  attribution: CartAttribution;
  cart: CartLine[];
  quote: CartLine[];
};

export const CART_PERSIST_KEY = "karzar.storefront.cart";
const PERSIST_FORMAT_VERSION = 2;

const SYNC_ERROR_MESSAGE =
  "همگام‌سازی سبد با سرور ناموفق بود. سبد محلی حفظ شد؛ می‌توانید ادامه دهید.";

/** Captured before async cart mutations; publish/clear only while still current. */
export type CartOwnershipFence =
  | { kind: "customer"; session: CustomerSessionFence }
  | { kind: "guest"; guestToken: string; generation: number };

type CartOpFence = CartOwnershipFence;

/**
 * Two carts coexist per the storefront "two-lane purchase" strategy:
 * - `cart`  → priced products (standard checkout).
 * - `quote` → products without a price (request-for-quote / pre-invoice).
 *
 * Visible `cart`/`quote` are publication surfaces. Attributed stash is the
 * persisted owner-scoped record (guest token G or verified customer id).
 */
interface CartState {
  /** Persisted attributed lanes (may be hidden while identity is unverified). */
  stash: CartStash | null;
  cart: CartLine[];
  quote: CartLine[];
  lastSyncError: string | null;
  addToCart: (product: ProductSummary, quantity?: number) => void;
  addToQuote: (product: ProductSummary, quantity?: number) => void;
  removeFromCart: (productId: number) => void;
  removeFromQuote: (productId: number) => void;
  setCartQuantity: (productId: number, quantity: number) => void;
  setQuoteQuantity: (productId: number, quantity: number) => void;
  clearCart: () => void;
  clearQuote: () => void;
  /** Clear quote only if the captured ownership fence is still current. */
  clearQuoteIfOwnershipCurrent: (fence: CartOwnershipFence) => boolean;
  /** Clear purchase cart only if the captured ownership fence is still current. */
  clearCartIfOwnershipCurrent: (fence: CartOwnershipFence) => boolean;
  /**
   * Restore inquiry lines under a captured verified-customer fence.
   * Returns false (no write) when the fence is stale or owner mismatched.
   */
  restoreQuote: (lines: CartLine[], fence: CustomerSessionFence) => boolean;
  clearSyncError: () => void;
  /** Hide published lines without server mutations or relabeling attribution. */
  hidePublishedCart: () => void;
  /** Publish stash only when attribution matches verified customer. */
  publishStashForVerifiedCustomer: (customerId: number) => void;
  /**
   * Republish guest stash after rehydrate when token matches exactly.
   * Never publishes customer stash. Safe after mount only.
   */
  publishStashForCurrentGuestIfMatches: () => boolean;
  /** Capture ownership fence for the currently attributable active stash. */
  captureOwnershipFence: () => CartOwnershipFence | null;
  /**
   * Same-owner reconcile: merge server lanes with local-only lines that share
   * the active attribution; upsert those local-only lines under the same owner.
   */
  reconcileSameOwnerFromServer: () => Promise<{ ok: boolean; error?: string }>;
  /**
   * Authorized guest→customer transfer: merge guestToken G, adopt only stash
   * attributed to G, then same-owner reconcile as customer.
   */
  transferGuestCartToCustomer: (
    guestToken: string,
    customerId: number,
  ) => Promise<{ ok: boolean; error?: string; mergeFailed?: boolean }>;
  /**
   * Customer-switch / cold cross-account: server is authoritative; local lines
   * from another owner are discarded.
   */
  replaceFromServerForCustomer: (
    customerId: number,
  ) => Promise<{ ok: boolean; error?: string }>;
  /**
   * Explicit active-scope entry for UI (cart page / checkout). Routes only after
   * validating verified identity + stash attribution — never guesses ownership.
   */
  reconcileActiveScopeFromServer: () => Promise<{ ok: boolean; error?: string }>;
  /**
   * @deprecated Use an explicit ownership operation. Kept as an alias that
   * delegates to reconcileActiveScopeFromServer (no local-only cross-owner push).
   */
  reconcileFromServer: () => Promise<{ ok: boolean; error?: string }>;
}

function upsert(lines: CartLine[], product: ProductSummary, quantity: number): CartLine[] {
  const existing = lines.find((l) => l.product.id === product.id);
  if (existing) {
    return lines.map((l) =>
      l.product.id === product.id ? { ...l, quantity: l.quantity + quantity } : l,
    );
  }
  return [...lines, { product, quantity }];
}

function stubProduct(item: CartItemResponse): ProductSummary {
  return {
    id: item.product_id,
    sku: "",
    name: item.product_name ?? `محصول #${item.product_id}`,
    thumbnail: null,
    base_price: item.base_price ?? null,
    stock_status: "in_stock",
    availability: true,
    is_original: false,
    category: null,
    brand: null,
  };
}

function setSyncError(message: string | null) {
  useCartStore.setState({ lastSyncError: message });
}

function attributionEquals(a: CartAttribution | null | undefined, b: CartAttribution | null | undefined): boolean {
  if (!a || !b) return false;
  if (a.kind !== b.kind) return false;
  if (a.kind === "guest" && b.kind === "guest") return a.guestToken === b.guestToken;
  if (a.kind === "customer" && b.kind === "customer") return a.customerId === b.customerId;
  return false;
}

function captureCartOpFence(attribution: CartAttribution): CartOpFence | null {
  if (attribution.kind === "customer") {
    const session = captureVerifiedCustomerSessionFence();
    if (!session || session.ownerId !== attribution.customerId) return null;
    return { kind: "customer", session };
  }
  const snap = getCustomerSessionSnapshot();
  // Guest ops are blocked while a verified customer owns the session.
  if (snap.phase === "verified" && snap.verifiedCustomerId != null) return null;
  const token = getCartToken();
  // Guest fence requires exact storage token match (G1 stash + G2 token fails closed).
  if (!token || token !== attribution.guestToken) return null;
  return {
    kind: "guest",
    guestToken: attribution.guestToken,
    generation: snap.generation,
  };
}

function isCartOpFenceCurrent(fence: CartOpFence | null): boolean {
  if (fence == null) return false;
  if (fence.kind === "customer") {
    return isCustomerSessionFenceCurrent(fence.session);
  }
  const snap = getCustomerSessionSnapshot();
  if (snap.generation !== fence.generation) return false;
  if (snap.phase === "verified" && snap.verifiedCustomerId != null) return false;
  const stash = useCartStore.getState().stash;
  const token = getCartToken();
  return (
    stash?.attribution.kind === "guest" &&
    stash.attribution.guestToken === fence.guestToken &&
    token === fence.guestToken
  );
}

export function isCartOwnershipFenceCurrent(fence: CartOwnershipFence | null): boolean {
  return isCartOpFenceCurrent(fence);
}

function writeStash(
  attribution: CartAttribution,
  cart: CartLine[],
  quote: CartLine[],
): CartStash {
  return { attribution, cart, quote };
}

/**
 * Establish attribution for a NEW mutation under the current identity.
 * On cross-attribution transition, never copy unproven visible lines —
 * start empty lanes, then apply only the new mutation.
 */
function ensureMutationAttribution(): CartAttribution | null {
  const verified = getVerifiedCustomerId();
  if (verified != null) {
    const next: CartAttribution = { kind: "customer", customerId: verified };
    const state = useCartStore.getState();
    if (!attributionEquals(state.stash?.attribution, next)) {
      useCartStore.setState({
        stash: writeStash(next, [], []),
        cart: [],
        quote: [],
      });
    }
    return next;
  }

  // Guest scope — token must be created under an explicit guest attribution.
  const token = getOrCreateCartToken();
  const next: CartAttribution = { kind: "guest", guestToken: token };
  const state = useCartStore.getState();
  if (!attributionEquals(state.stash?.attribution, next)) {
    // New guest scope replaces any prior customer/foreign stash (fail closed).
    useCartStore.setState({
      stash: writeStash(next, [], []),
      cart: [],
      quote: [],
    });
  }
  return next;
}

/**
 * Existing-stash mutations (remove/set/clear) require the stash to already
 * belong to the current active identity. Never reuse a foreign attribution.
 */
function resolveExistingMutationAttribution(): CartAttribution | null {
  const verified = getVerifiedCustomerId();
  const stash = useCartStore.getState().stash;
  if (verified != null) {
    if (
      stash?.attribution.kind === "customer" &&
      stash.attribution.customerId === verified
    ) {
      return stash.attribution;
    }
    return null;
  }
  const token = getCartToken();
  if (
    token &&
    stash?.attribution.kind === "guest" &&
    stash.attribution.guestToken === token
  ) {
    return stash.attribution;
  }
  return null;
}

async function syncServerCart(lane: CartLane, productId: number, lines: CartLine[]) {
  if (env.USE_MOCK) return;
  const attribution = useCartStore.getState().stash?.attribution;
  if (!attribution) return;
  const fence = captureCartOpFence(attribution);
  if (!fence) return;
  const line = lines.find((l) => l.product.id === productId);
  if (!line) return;
  try {
    await cartService.upsertItem(lane, productId, line.quantity);
    if (!isCartOpFenceCurrent(fence)) return;
    setSyncError(null);
  } catch {
    if (!isCartOpFenceCurrent(fence)) return;
    setSyncError("همگام‌سازی سبد با سرور ناموفق بود. تغییرات محلی حفظ شد.");
  }
}

async function removeServerCartItem(lane: CartLane, productId: number) {
  if (env.USE_MOCK) return;
  const attribution = useCartStore.getState().stash?.attribution;
  if (!attribution) return;
  const fence = captureCartOpFence(attribution);
  if (!fence) return;
  try {
    await cartService.removeItem(lane, productId);
    if (!isCartOpFenceCurrent(fence)) return;
    setSyncError(null);
  } catch {
    if (!isCartOpFenceCurrent(fence)) return;
    setSyncError("حذف آیتم از سبد سرور ناموفق بود.");
  }
}

async function clearServerCart(lane: CartLane) {
  if (env.USE_MOCK) return;
  const attribution = useCartStore.getState().stash?.attribution;
  if (!attribution) return;
  const fence = captureCartOpFence(attribution);
  if (!fence) return;
  try {
    await cartService.clear(lane);
    if (!isCartOpFenceCurrent(fence)) return;
    setSyncError(null);
  } catch {
    if (!isCartOpFenceCurrent(fence)) return;
    setSyncError("پاک‌سازی سبد سرور ناموفق بود.");
  }
}

async function fetchServerLanes(): Promise<{
  purchaseLines: CartLine[];
  inquiryLines: CartLine[];
}> {
  const [purchase, inquiry] = await Promise.all([
    cartService.get("purchase"),
    cartService.get("inquiry"),
  ]);

  const ids = [
    ...new Set([
      ...purchase.items.map((i) => i.product_id),
      ...inquiry.items.map((i) => i.product_id),
    ]),
  ];

  let byId = new Map<number, ProductSummary>();
  if (ids.length > 0) {
    const { catalogService } = await import("@/services/catalog");
    const products = await catalogService.getProductsByIds(ids);
    byId = new Map(products.map((p) => [p.id, p]));
  }

  const localById = new Map<number, ProductSummary>();
  const state = useCartStore.getState();
  for (const line of [...state.cart, ...state.quote, ...(state.stash?.cart ?? []), ...(state.stash?.quote ?? [])]) {
    localById.set(line.product.id, line.product);
  }

  const toLines = (items: CartItemResponse[]): CartLine[] =>
    items.map((item) => ({
      product:
        byId.get(item.product_id) ??
        localById.get(item.product_id) ??
        stubProduct(item),
      quantity: item.quantity,
    }));

  return {
    purchaseLines: toLines(purchase.items),
    inquiryLines: toLines(inquiry.items),
  };
}

function applyPublishedAndStash(
  attribution: CartAttribution,
  cart: CartLine[],
  quote: CartLine[],
  lastSyncError: string | null = null,
) {
  useCartStore.setState({
    stash: writeStash(attribution, cart, quote),
    cart,
    quote,
    lastSyncError,
  });
}

type CartPersistSlice = {
  stash: CartStash | null;
};

function isCartLine(value: unknown): value is CartLine {
  if (!value || typeof value !== "object") return false;
  const line = value as CartLine;
  return (
    typeof line.quantity === "number" &&
    line.product != null &&
    typeof line.product === "object" &&
    typeof line.product.id === "number"
  );
}

function normalizeAttribution(raw: unknown): CartAttribution | null {
  if (!raw || typeof raw !== "object") return null;
  const attr = raw as CartAttribution;
  if (attr.kind === "guest" && typeof attr.guestToken === "string" && attr.guestToken.length >= 32) {
    return { kind: "guest", guestToken: attr.guestToken };
  }
  if (
    attr.kind === "customer" &&
    typeof attr.customerId === "number" &&
    Number.isFinite(attr.customerId) &&
    attr.customerId > 0
  ) {
    return { kind: "customer", customerId: attr.customerId };
  }
  return null;
}

function normalizeStash(raw: unknown): CartStash | null {
  if (!raw || typeof raw !== "object") return null;
  const candidate = raw as CartStash;
  const attribution = normalizeAttribution(candidate.attribution);
  if (!attribution) return null;
  const cart = Array.isArray(candidate.cart) ? candidate.cart.filter(isCartLine) : [];
  const quote = Array.isArray(candidate.quote) ? candidate.quote.filter(isCartLine) : [];
  if (cart.length === 0 && quote.length === 0) {
    return { attribution, cart: [], quote: [] };
  }
  return { attribution, cart, quote };
}

/**
 * Legacy v1 `{ cart, quote }` has no owner — discard (fail closed).
 * Never adopt via customer hint, cart token, or session marker.
 */
function migratePersistedState(persisted: unknown): CartPersistSlice {
  if (!persisted || typeof persisted !== "object") {
    return { stash: null };
  }
  const obj = persisted as Record<string, unknown>;
  if ("stash" in obj) {
    return { stash: normalizeStash(obj.stash) };
  }
  // Legacy unattributed envelope
  if ("cart" in obj || "quote" in obj) {
    return { stash: null };
  }
  return { stash: null };
}

export function migrateCartPersistForTests(persisted: unknown): CartPersistSlice {
  return migratePersistedState(persisted);
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      stash: null,
      cart: [],
      quote: [],
      lastSyncError: null,

      hidePublishedCart: () => {
        set({ cart: [], quote: [], lastSyncError: null });
      },

      publishStashForVerifiedCustomer: (customerId: number) => {
        const verified = getVerifiedCustomerId();
        if (verified == null || verified !== customerId) {
          set({ cart: [], quote: [] });
          return;
        }
        const stash = get().stash;
        if (
          stash?.attribution.kind === "customer" &&
          stash.attribution.customerId === customerId
        ) {
          set({
            cart: stash.cart,
            quote: stash.quote,
            lastSyncError: null,
          });
          return;
        }
        // Foreign or guest stash must not publish under this customer.
        set({ cart: [], quote: [] });
      },

      publishStashForCurrentGuestIfMatches: () => {
        if (getVerifiedCustomerId() != null) return false;
        const token = getCartToken();
        const stash = get().stash;
        if (
          !token ||
          stash?.attribution.kind !== "guest" ||
          stash.attribution.guestToken !== token
        ) {
          return false;
        }
        set({
          cart: stash.cart,
          quote: stash.quote,
          lastSyncError: null,
        });
        return true;
      },

      captureOwnershipFence: () => {
        const stash = get().stash;
        if (!stash) return null;
        return captureCartOpFence(stash.attribution);
      },

      addToCart: (product, quantity = 1) => {
        const attribution = ensureMutationAttribution();
        if (!attribution) return;
        set((s) => {
          const cart = upsert(s.cart, product, quantity);
          return {
            cart,
            stash: writeStash(attribution, cart, s.quote),
          };
        });
        void syncServerCart("purchase", product.id, get().cart);
      },

      addToQuote: (product, quantity = 1) => {
        const attribution = ensureMutationAttribution();
        if (!attribution) return;
        set((s) => {
          const quote = upsert(s.quote, product, quantity);
          return {
            quote,
            stash: writeStash(attribution, s.cart, quote),
          };
        });
        void syncServerCart("inquiry", product.id, get().quote);
      },

      removeFromCart: (productId) => {
        const attribution = resolveExistingMutationAttribution();
        if (!attribution) return;
        set((s) => {
          const cart = s.cart.filter((l) => l.product.id !== productId);
          return {
            cart,
            stash: writeStash(attribution, cart, s.quote),
          };
        });
        void removeServerCartItem("purchase", productId);
      },

      removeFromQuote: (productId) => {
        const attribution = resolveExistingMutationAttribution();
        if (!attribution) return;
        set((s) => {
          const quote = s.quote.filter((l) => l.product.id !== productId);
          return {
            quote,
            stash: writeStash(attribution, s.cart, quote),
          };
        });
        void removeServerCartItem("inquiry", productId);
      },

      setCartQuantity: (productId, quantity) => {
        if (quantity < 1) {
          get().removeFromCart(productId);
          return;
        }
        const attribution = resolveExistingMutationAttribution();
        if (!attribution) return;
        set((s) => {
          const cart = s.cart.map((l) =>
            l.product.id === productId ? { ...l, quantity } : l,
          );
          return {
            cart,
            stash: writeStash(attribution, cart, s.quote),
          };
        });
        void syncServerCart("purchase", productId, get().cart);
      },

      setQuoteQuantity: (productId, quantity) => {
        if (quantity < 1) {
          get().removeFromQuote(productId);
          return;
        }
        const attribution = resolveExistingMutationAttribution();
        if (!attribution) return;
        set((s) => {
          const quote = s.quote.map((l) =>
            l.product.id === productId ? { ...l, quantity } : l,
          );
          return {
            quote,
            stash: writeStash(attribution, s.cart, quote),
          };
        });
        void syncServerCart("inquiry", productId, get().quote);
      },

      clearCart: () => {
        const attribution = resolveExistingMutationAttribution();
        if (!attribution) {
          // Fail closed: may clear published surface only; never rewrite foreign stash.
          set({ cart: [] });
          return;
        }
        set((s) => ({
          cart: [],
          stash: writeStash(attribution, [], s.quote),
        }));
        void clearServerCart("purchase");
      },

      clearQuote: () => {
        const attribution = resolveExistingMutationAttribution();
        if (!attribution) {
          set({ quote: [] });
          return;
        }
        set((s) => ({
          quote: [],
          stash: writeStash(attribution, s.cart, []),
        }));
        void clearServerCart("inquiry");
      },

      clearQuoteIfOwnershipCurrent: (fence) => {
        if (!isCartOpFenceCurrent(fence)) return false;
        const attribution = resolveExistingMutationAttribution();
        if (!attribution) return false;
        if (fence.kind === "customer") {
          if (
            attribution.kind !== "customer" ||
            attribution.customerId !== fence.session.ownerId
          ) {
            return false;
          }
        } else if (
          attribution.kind !== "guest" ||
          attribution.guestToken !== fence.guestToken
        ) {
          return false;
        }
        set((s) => ({
          quote: [],
          stash: writeStash(attribution, s.cart, []),
        }));
        void clearServerCart("inquiry");
        return true;
      },

      clearCartIfOwnershipCurrent: (fence) => {
        if (!isCartOpFenceCurrent(fence)) return false;
        const attribution = resolveExistingMutationAttribution();
        if (!attribution) return false;
        if (fence.kind === "customer") {
          if (
            attribution.kind !== "customer" ||
            attribution.customerId !== fence.session.ownerId
          ) {
            return false;
          }
        } else if (
          attribution.kind !== "guest" ||
          attribution.guestToken !== fence.guestToken
        ) {
          return false;
        }
        set((s) => ({
          cart: [],
          stash: writeStash(attribution, [], s.quote),
        }));
        void clearServerCart("purchase");
        return true;
      },

      restoreQuote: (lines, fence) => {
        // Store-level ownership gate — callers must pass the fence captured
        // before any await that produced `lines`. Reading the current verified
        // id alone is insufficient after an async boundary.
        if (!isCustomerSessionFenceCurrent(fence)) return false;
        const verified = getVerifiedCustomerId();
        if (verified == null || verified !== fence.ownerId) return false;

        const stash = get().stash;
        // Never inject into a foreign customer stash.
        if (
          stash?.attribution.kind === "customer" &&
          stash.attribution.customerId !== fence.ownerId
        ) {
          return false;
        }

        const attribution: CartAttribution = {
          kind: "customer",
          customerId: fence.ownerId,
        };
        set((s) => ({
          quote: lines,
          stash: writeStash(attribution, s.cart, lines),
          lastSyncError: null,
        }));
        return true;
      },

      clearSyncError: () => set({ lastSyncError: null }),

      reconcileSameOwnerFromServer: async () => {
        const attribution = get().stash?.attribution;
        if (!attribution) {
          return { ok: false, error: SYNC_ERROR_MESSAGE };
        }
        // Guest path requires exact token match at capture (G1 stash / G2 token fails closed).
        const fence = captureCartOpFence(attribution);
        if (!fence) {
          return { ok: false, error: SYNC_ERROR_MESSAGE };
        }

        if (env.USE_MOCK) {
          if (!isCartOpFenceCurrent(fence)) {
            return { ok: false, error: "CART_STALE_OWNER" };
          }
          set({ lastSyncError: null });
          return { ok: true };
        }

        // Local-only candidates must already belong to this attribution.
        const localCart = get().stash?.cart ?? get().cart;
        const localQuote = get().stash?.quote ?? get().quote;

        try {
          const { purchaseLines, inquiryLines } = await fetchServerLanes();
          if (!isCartOpFenceCurrent(fence)) {
            return { ok: false, error: "CART_STALE_OWNER" };
          }

          const purchaseIds = new Set(purchaseLines.map((l) => l.product.id));
          const inquiryIds = new Set(inquiryLines.map((l) => l.product.id));
          const localOnlyCart = localCart.filter((l) => !purchaseIds.has(l.product.id));
          const localOnlyQuote = localQuote.filter((l) => !inquiryIds.has(l.product.id));

          const nextCart = [...purchaseLines, ...localOnlyCart];
          const nextQuote = [...inquiryLines, ...localOnlyQuote];
          applyPublishedAndStash(attribution, nextCart, nextQuote, null);

          for (const line of localOnlyCart) {
            if (!isCartOpFenceCurrent(fence)) break;
            void cartService.upsertItem("purchase", line.product.id, line.quantity).catch(() => {
              if (isCartOpFenceCurrent(fence)) setSyncError(SYNC_ERROR_MESSAGE);
            });
          }
          for (const line of localOnlyQuote) {
            if (!isCartOpFenceCurrent(fence)) break;
            void cartService.upsertItem("inquiry", line.product.id, line.quantity).catch(() => {
              if (isCartOpFenceCurrent(fence)) setSyncError(SYNC_ERROR_MESSAGE);
            });
          }

          return { ok: true };
        } catch {
          if (isCartOpFenceCurrent(fence)) {
            set({ lastSyncError: SYNC_ERROR_MESSAGE });
          }
          return { ok: false, error: SYNC_ERROR_MESSAGE };
        }
      },

      transferGuestCartToCustomer: async (guestToken, customerId) => {
        if (!guestToken || guestToken.length < 32) {
          return { ok: false, error: SYNC_ERROR_MESSAGE, mergeFailed: true };
        }

        const session = captureVerifiedCustomerSessionFence();
        if (!session || session.ownerId !== customerId) {
          return { ok: false, error: SYNC_ERROR_MESSAGE };
        }

        // Transfer source requires stash G AND current storage token G at capture.
        if (getCartToken() !== guestToken) {
          return { ok: false, error: SYNC_ERROR_MESSAGE, mergeFailed: true };
        }
        const stash = get().stash;
        const guestOwned =
          stash?.attribution.kind === "guest" && stash.attribution.guestToken === guestToken
            ? stash
            : null;
        if (!guestOwned) {
          // Authorization requires source provenance still be exact guest G.
          return { ok: false, error: SYNC_ERROR_MESSAGE, mergeFailed: true };
        }

        // Capture authorized transfer candidate before awaits can reclassify it.
        const authz = {
          guestToken,
          customerId,
          session,
          guestLocalCart: guestOwned.cart,
          guestLocalQuote: guestOwned.quote,
        };

        const sourceStillAuthorized = (): boolean => {
          if (!isCustomerSessionFenceCurrent(authz.session)) return false;
          if (getVerifiedCustomerId() !== authz.customerId) return false;
          const current = get().stash;
          // Source G may still be present, or we may already be mid-transfer as customer A.
          if (
            current?.attribution.kind === "guest" &&
            current.attribution.guestToken === authz.guestToken
          ) {
            // Token-only race: stash still G1 but storage already G2 → refuse.
            return getCartToken() === authz.guestToken;
          }
          if (
            current?.attribution.kind === "customer" &&
            current.attribution.customerId === authz.customerId
          ) {
            return true;
          }
          // Replaced by G2 / foreign customer — refuse local publication.
          return false;
        };

        if (env.USE_MOCK) {
          if (!sourceStillAuthorized()) {
            return { ok: false, error: "CART_STALE_OWNER" };
          }
          const attr: CartAttribution = { kind: "customer", customerId: authz.customerId };
          applyPublishedAndStash(attr, authz.guestLocalCart, authz.guestLocalQuote, null);
          clearCartTokenIfMatches(authz.guestToken);
          if (!sourceStillAuthorized()) {
            set({ cart: [], quote: [] });
            return { ok: false, error: "CART_STALE_OWNER" };
          }
          return { ok: true };
        }

        try {
          await cartService.merge(authz.guestToken);
          // Stale server merge for A is not locally reversible (not F04). Refuse local side effects.
          // While stash is still guest G, storage token must still equal G (token-only race).
          if (!sourceStillAuthorized()) {
            return { ok: false, error: "CART_STALE_OWNER" };
          }

          // Adopt customer ownership BEFORE retiring the guest token so the
          // post-clear authorization check uses the customer path (token N/A).
          const attr: CartAttribution = { kind: "customer", customerId: authz.customerId };
          set({
            stash: writeStash(attr, authz.guestLocalCart, authz.guestLocalQuote),
            cart: authz.guestLocalCart,
            quote: authz.guestLocalQuote,
          });

          clearCartTokenIfMatches(authz.guestToken);
          if (!sourceStillAuthorized()) {
            // Do not start reconcile that could upsert under a newer owner.
            set({ cart: [], quote: [] });
            return { ok: false, error: "CART_STALE_OWNER" };
          }

          const result = await get().reconcileSameOwnerFromServer();
          if (!sourceStillAuthorized()) {
            set({ cart: [], quote: [] });
            return { ok: false, error: "CART_STALE_OWNER" };
          }
          return result;
        } catch {
          if (isCustomerSessionFenceCurrent(authz.session)) {
            // Do not relabel guest lines as customer on merge failure.
            const current = get().stash;
            if (
              current?.attribution.kind === "guest" &&
              current.attribution.guestToken === authz.guestToken
            ) {
              set({
                stash: current,
                cart: [],
                quote: [],
                lastSyncError: "همگام‌سازی سبد با سرور ناموفق بود. سبد محلی حفظ شد.",
              });
            } else if (!current) {
              set({
                stash: {
                  attribution: { kind: "guest", guestToken: authz.guestToken },
                  cart: authz.guestLocalCart,
                  quote: authz.guestLocalQuote,
                },
                cart: [],
                quote: [],
                lastSyncError: "همگام‌سازی سبد با سرور ناموفق بود. سبد محلی حفظ شد.",
              });
            } else {
              set({
                lastSyncError: "همگام‌سازی سبد با سرور ناموفق بود. سبد محلی حفظ شد.",
              });
            }
          }
          return {
            ok: false,
            error: "همگام‌سازی سبد با سرور ناموفق بود. سبد محلی حفظ شد.",
            mergeFailed: true,
          };
        }
      },

      replaceFromServerForCustomer: async (customerId) => {
        if (env.USE_MOCK) {
          const attr: CartAttribution = { kind: "customer", customerId };
          applyPublishedAndStash(attr, [], [], null);
          return { ok: true };
        }

        const session = captureVerifiedCustomerSessionFence();
        if (!session || session.ownerId !== customerId) {
          return { ok: false, error: SYNC_ERROR_MESSAGE };
        }

        try {
          const { purchaseLines, inquiryLines } = await fetchServerLanes();
          if (!isCustomerSessionFenceCurrent(session)) {
            return { ok: false, error: "CART_STALE_OWNER" };
          }
          const attr: CartAttribution = { kind: "customer", customerId };
          applyPublishedAndStash(attr, purchaseLines, inquiryLines, null);
          return { ok: true };
        } catch {
          if (isCustomerSessionFenceCurrent(session)) {
            // Fail closed: do not publish foreign stash as this customer.
            set({
              cart: [],
              quote: [],
              stash: writeStash({ kind: "customer", customerId }, [], []),
              lastSyncError: SYNC_ERROR_MESSAGE,
            });
          }
          return { ok: false, error: SYNC_ERROR_MESSAGE };
        }
      },

      reconcileActiveScopeFromServer: async () => {
        // Ownership/publication first — USE_MOCK may skip HTTP, never skip publication.
        const verified = getVerifiedCustomerId();
        if (verified != null) {
          const stash = get().stash;
          if (
            stash?.attribution.kind === "customer" &&
            stash.attribution.customerId === verified
          ) {
            get().publishStashForVerifiedCustomer(verified);
            return get().reconcileSameOwnerFromServer();
          }
          // Foreign customer, guest, or empty stash → server-authoritative replace.
          return get().replaceFromServerForCustomer(verified);
        }

        const published = get().publishStashForCurrentGuestIfMatches();
        if (!published) {
          // Mismatched guest token or customer stash while unverified — keep hidden.
          set({ cart: [], quote: [], lastSyncError: null });
          return { ok: true };
        }
        return get().reconcileSameOwnerFromServer();
      },

      reconcileFromServer: async () => get().reconcileActiveScopeFromServer(),
    }),
    {
      name: CART_PERSIST_KEY,
      version: PERSIST_FORMAT_VERSION,
      partialize: (state) => ({ stash: state.stash }),
      migrate: (persisted) => migratePersistedState(persisted),
      // Defer localStorage merge until after mount (Providers PersistRehydrate).
      // Eager hydrate schedules setState via microtask during SSR hydration → React 19 warning.
      skipHydration: true,
      merge: (persistedState, currentState) => {
        const migrated = migratePersistedState(persistedState);
        // Never auto-publish customer stash before verified session.
        return {
          ...currentState,
          stash: migrated.stash,
          cart: [],
          quote: [],
        };
      },
    },
  ),
);

export const selectCartCount = (s: CartState) =>
  s.cart.reduce((sum, l) => sum + l.quantity, 0);
export const selectQuoteCount = (s: CartState) =>
  s.quote.reduce((sum, l) => sum + l.quantity, 0);
