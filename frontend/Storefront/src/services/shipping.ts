import { apiClient } from "@/lib/api-client";
import { env } from "@/config/env";
import type {
  ShippingCity,
  ShippingMethodOption,
  ShippingQuoteResponse,
  ShippingStatus,
} from "@/types/shipping";

export const shippingService = {
  async status(): Promise<ShippingStatus> {
    if (env.USE_MOCK) {
      return {
        enabled: true,
        quote_ttl_seconds: 600,
        checkout_quote_required: false,
        booking_enabled: false,
        method_selection_enabled: true,
        shipping_payment_mode: "receiver_due",
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

  async methodOptions(payload: {
    province: string;
    city: string;
    postal_code?: string;
  }): Promise<ShippingMethodOption[]> {
    if (env.USE_MOCK) {
      const tehran = payload.city.trim() === "تهران" && payload.province.trim() === "تهران";
      const base = [
        { code: "tipax_standard", title: "تیپاکس", payment_mode: "receiver_due", price: null, price_label: "پس‌کرایه" },
        { code: "chapar_standard", title: "چاپار", payment_mode: "receiver_due", price: null, price_label: "پس‌کرایه" },
      ];
      if (tehran) {
        return [
          { code: "tehran_express", title: "ارسال فوری تهران", payment_mode: "receiver_due", price: null, price_label: "پس‌کرایه" },
          ...base,
        ];
      }
      return base;
    }
    const { data } = await apiClient.post<{ options: ShippingMethodOption[] }>(
      "/shipping/options",
      payload,
    );
    return data.options;
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
