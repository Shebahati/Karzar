/**
 * Server cart facade — dual-lane (purchase | inquiry).
 * Guest identity via X-Cart-Token (auto-attached by api-client).
 * Local Zustand cart remains the UX source; this syncs when live API is on.
 */

import { apiClient, getOrCreateCartToken } from "@/lib/api-client";
import { env } from "@/config/env";

export type CartLane = "purchase" | "inquiry";

export interface CartItemResponse {
  product_id: number;
  quantity: number;
  product_name?: string;
  base_price?: string | null;
  stock_quantity?: string | null;
}

export interface CartResponse {
  lane: CartLane;
  items: CartItemResponse[];
  item_count: number;
}

export const cartService = {
  ensureGuestToken(): string {
    return getOrCreateCartToken();
  },

  async get(lane: CartLane = "purchase"): Promise<CartResponse> {
    if (env.USE_MOCK) return { lane, items: [], item_count: 0 };
    this.ensureGuestToken();
    const { data } = await apiClient.get<CartResponse>("/cart", { params: { lane } });
    return data;
  },

  async upsertItem(
    lane: CartLane,
    productId: number,
    quantity: number,
  ): Promise<CartResponse> {
    if (env.USE_MOCK) {
      return { lane, items: [{ product_id: productId, quantity }], item_count: 1 };
    }
    this.ensureGuestToken();
    const { data } = await apiClient.put<CartResponse>("/cart/items", {
      lane,
      product_id: productId,
      quantity,
    });
    return data;
  },

  async removeItem(lane: CartLane, productId: number): Promise<CartResponse> {
    if (env.USE_MOCK) return { lane, items: [], item_count: 0 };
    this.ensureGuestToken();
    const { data } = await apiClient.delete<CartResponse>(`/cart/items/${productId}`, {
      params: { lane },
    });
    return data;
  },

  async clear(lane: CartLane): Promise<void> {
    if (env.USE_MOCK) return;
    this.ensureGuestToken();
    await apiClient.delete("/cart", { params: { lane } });
  },

  async merge(guestToken: string, lane?: CartLane): Promise<CartResponse[]> {
    if (env.USE_MOCK) return [];
    const { data } = await apiClient.post<CartResponse[]>("/cart/merge", {
      guest_token: guestToken,
      lane,
    });
    return data;
  },
};
