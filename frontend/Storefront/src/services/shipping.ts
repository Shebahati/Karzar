import { apiClient } from "@/lib/api-client";
import { env } from "@/config/env";
import type {
  ShippingCity,
  ShippingQuoteResponse,
  ShippingStatus,
} from "@/types/shipping";

export const shippingService = {
  async status(): Promise<ShippingStatus> {
    if (env.USE_MOCK) {
      return {
        enabled: false,
        quote_ttl_seconds: 600,
        checkout_quote_required: false,
        booking_enabled: false,
      };
    }
    const { data } = await apiClient.get<ShippingStatus>("/shipping/status");
    return data;
  },

  async cities(): Promise<ShippingCity[]> {
    if (env.USE_MOCK) return [];
    const { data } = await apiClient.get<{ data: ShippingCity[] }>("/shipping/cities");
    return data.data;
  },

  async quotes(payload: {
    items: Array<{ product_id: number; quantity: number }>;
    location_code: number;
    postal_code?: string;
    city_name?: string;
    province_name?: string;
  }): Promise<ShippingQuoteResponse> {
    if (env.USE_MOCK) {
      throw new Error("ارسال پستی در حالت نمایشی فعال نیست.");
    }
    const { data } = await apiClient.post<ShippingQuoteResponse>("/shipping/quotes", payload);
    return data;
  },
};
