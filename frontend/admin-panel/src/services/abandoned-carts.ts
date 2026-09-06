import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/common";

export interface AbandonedCartItem {
  product_id: number;
  quantity: number;
  product_name: string | null;
  product_sku: string | null;
}

export interface AbandonedCartSummary {
  cart_id: number;
  user_id: number | null;
  customer_name: string;
  customer_phone: string | null;
  item_count: number;
  cart_value: string;
  last_activity_at: string;
  items: AbandonedCartItem[];
}

export const abandonedCartsService = {
  async list(params: { skip?: number; limit?: number } = {}) {
    const { data } = await apiClient.get<PaginatedResponse<AbandonedCartSummary>>(
      "/abandoned-carts",
      { params },
    );
    return data;
  },
};
