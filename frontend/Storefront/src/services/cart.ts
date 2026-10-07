/**
 * Server cart facade — dual-lane (purchase | inquiry).
 *
 * Transport identity:
 * - `customer` → credentialed apiClient (cookies + optional Bearer)
 * - `guest` → guestCartClient (X-Cart-Token only; withCredentials:false)
 *
 * Merge is always authenticated (verified customer target).
 */

import { apiClient, guestCartClient, getOrCreateCartToken } from "@/lib/api-client";
import { env } from "@/config/env";
import type { AxiosInstance } from "axios";

export type CartLane = "purchase" | "inquiry";

/** Explicit wire identity for cart HTTP — never infer from soft login markers. */
export type CartTransport = "customer" | "guest";

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

function clientFor(transport: CartTransport): AxiosInstance {
  return transport === "guest" ? guestCartClient : apiClient;
}

export const cartService = {
  ensureGuestToken(): string {
    return getOrCreateCartToken();
  },

  /** Inspectable for tests — proves guest vs credentialed selection. */
  resolveTransportClient(transport: CartTransport): AxiosInstance {
    return clientFor(transport);
  },

  async get(
    lane: CartLane = "purchase",
    transport: CartTransport = "customer",
  ): Promise<CartResponse> {
    if (env.USE_MOCK) return { lane, items: [], item_count: 0 };
    if (transport === "guest") this.ensureGuestToken();
    const { data } = await clientFor(transport).get<CartResponse>("/cart", {
      params: { lane },
    });
    return data;
  },

  async upsertItem(
    lane: CartLane,
    productId: number,
    quantity: number,
    transport: CartTransport = "customer",
  ): Promise<CartResponse> {
    if (env.USE_MOCK) {
      return { lane, items: [{ product_id: productId, quantity }], item_count: 1 };
    }
    if (transport === "guest") this.ensureGuestToken();
    const { data } = await clientFor(transport).put<CartResponse>("/cart/items", {
      lane,
      product_id: productId,
      quantity,
    });
    return data;
  },

  async removeItem(
    lane: CartLane,
    productId: number,
    transport: CartTransport = "customer",
  ): Promise<CartResponse> {
    if (env.USE_MOCK) return { lane, items: [], item_count: 0 };
    if (transport === "guest") this.ensureGuestToken();
    const { data } = await clientFor(transport).delete<CartResponse>(
      `/cart/items/${productId}`,
      { params: { lane } },
    );
    return data;
  },

  async clear(lane: CartLane, transport: CartTransport = "customer"): Promise<void> {
    if (env.USE_MOCK) return;
    if (transport === "guest") this.ensureGuestToken();
    await clientFor(transport).delete("/cart", { params: { lane } });
  },

  /**
   * Authenticated transition only — verified customer fence required by caller.
   * Never uses guestCartClient.
   */
  async merge(guestToken: string, lane?: CartLane): Promise<CartResponse[]> {
    if (env.USE_MOCK) return [];
    const { data } = await apiClient.post<CartResponse[]>("/cart/merge", {
      guest_token: guestToken,
      lane,
    });
    return data;
  },
};
