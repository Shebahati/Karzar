"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ProductSummary } from "@/types/product";
import { cartService, type CartItemResponse, type CartLane } from "@/services/cart";
import { env } from "@/config/env";

export interface CartLine {
  product: ProductSummary;
  quantity: number;
}

/**
 * Two carts coexist per the storefront "two-lane purchase" strategy:
 * - `cart`  → priced products (standard checkout).
 * - `quote` → products without a price (request-for-quote / pre-invoice).
 * Local Zustand remains UX source of truth; live mode best-effort syncs to /cart.
 */
interface CartState {
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
  restoreQuote: (lines: CartLine[]) => void;
  clearSyncError: () => void;
  /** After login/merge: GET /cart for both lanes and reconcile into Zustand. */
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

async function syncServerCart(lane: CartLane, productId: number, lines: CartLine[]) {
  if (env.USE_MOCK) return;
  const line = lines.find((l) => l.product.id === productId);
  if (!line) return;
  try {
    await cartService.upsertItem(lane, productId, line.quantity);
    setSyncError(null);
  } catch {
    setSyncError("همگام‌سازی سبد با سرور ناموفق بود. تغییرات محلی حفظ شد.");
  }
}

async function removeServerCartItem(lane: CartLane, productId: number) {
  if (env.USE_MOCK) return;
  try {
    await cartService.removeItem(lane, productId);
    setSyncError(null);
  } catch {
    setSyncError("حذف آیتم از سبد سرور ناموفق بود.");
  }
}

async function clearServerCart(lane: CartLane) {
  if (env.USE_MOCK) return;
  try {
    await cartService.clear(lane);
    setSyncError(null);
  } catch {
    setSyncError("پاک‌سازی سبد سرور ناموفق بود.");
  }
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      cart: [],
      quote: [],
      lastSyncError: null,
      addToCart: (product, quantity = 1) => {
        set((s) => ({ cart: upsert(s.cart, product, quantity) }));
        void syncServerCart("purchase", product.id, get().cart);
      },
      addToQuote: (product, quantity = 1) => {
        set((s) => ({ quote: upsert(s.quote, product, quantity) }));
        void syncServerCart("inquiry", product.id, get().quote);
      },
      removeFromCart: (productId) => {
        set((s) => ({ cart: s.cart.filter((l) => l.product.id !== productId) }));
        void removeServerCartItem("purchase", productId);
      },
      removeFromQuote: (productId) => {
        set((s) => ({ quote: s.quote.filter((l) => l.product.id !== productId) }));
        void removeServerCartItem("inquiry", productId);
      },
      setCartQuantity: (productId, quantity) => {
        set((s) => ({
          cart: s.cart.map((l) =>
            l.product.id === productId ? { ...l, quantity: Math.max(1, quantity) } : l,
          ),
        }));
        void syncServerCart("purchase", productId, get().cart);
      },
      setQuoteQuantity: (productId, quantity) => {
        set((s) => ({
          quote: s.quote.map((l) =>
            l.product.id === productId ? { ...l, quantity: Math.max(1, quantity) } : l,
          ),
        }));
        void syncServerCart("inquiry", productId, get().quote);
      },
      clearCart: () => {
        set({ cart: [] });
        void clearServerCart("purchase");
      },
      clearQuote: () => {
        set({ quote: [] });
        void clearServerCart("inquiry");
      },
      restoreQuote: (lines) => set({ quote: lines }),
      clearSyncError: () => set({ lastSyncError: null }),
      reconcileFromServer: async () => {
        if (env.USE_MOCK) {
          set({ lastSyncError: null });
          return { ok: true };
        }

        const syncErrorMessage =
          "همگام‌سازی سبد با سرور ناموفق بود. سبد محلی حفظ شد؛ می‌توانید ادامه دهید.";

        try {
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
          for (const line of [...get().cart, ...get().quote]) {
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

          const purchaseLines = toLines(purchase.items);
          const inquiryLines = toLines(inquiry.items);
          const purchaseIds = new Set(purchaseLines.map((l) => l.product.id));
          const inquiryIds = new Set(inquiryLines.map((l) => l.product.id));

          // Keep local-only lines (not yet on server) and push them up best-effort.
          const localOnlyCart = get().cart.filter((l) => !purchaseIds.has(l.product.id));
          const localOnlyQuote = get().quote.filter((l) => !inquiryIds.has(l.product.id));

          set({
            cart: [...purchaseLines, ...localOnlyCart],
            quote: [...inquiryLines, ...localOnlyQuote],
            lastSyncError: null,
          });

          for (const line of localOnlyCart) {
            void cartService.upsertItem("purchase", line.product.id, line.quantity).catch(() => {
              setSyncError(syncErrorMessage);
            });
          }
          for (const line of localOnlyQuote) {
            void cartService.upsertItem("inquiry", line.product.id, line.quantity).catch(() => {
              setSyncError(syncErrorMessage);
            });
          }

          return { ok: true };
        } catch {
          set({ lastSyncError: syncErrorMessage });
          return { ok: false, error: syncErrorMessage };
        }
      },
    }),
    {
      name: "karzar.storefront.cart",
      partialize: (state) => ({ cart: state.cart, quote: state.quote }),
    },
  ),
);

export const selectCartCount = (s: CartState) =>
  s.cart.reduce((sum, l) => sum + l.quantity, 0);
export const selectQuoteCount = (s: CartState) =>
  s.quote.reduce((sum, l) => sum + l.quantity, 0);
