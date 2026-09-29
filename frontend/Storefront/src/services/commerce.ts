import { apiClient } from "@/lib/api-client";
import { env } from "@/config/env";

export type PurchaseCheckoutStatus = {
  purchase_checkout_enabled: boolean;
  message: string | null;
};

export const commerceService = {
  async purchaseStatus(): Promise<PurchaseCheckoutStatus> {
    if (env.USE_MOCK) {
      return { purchase_checkout_enabled: true, message: null };
    }
    const { data } = await apiClient.get<PurchaseCheckoutStatus>("/commerce/purchase-status");
    return data;
  },
};
