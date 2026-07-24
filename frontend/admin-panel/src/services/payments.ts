import { apiClient, withStepUp } from "@/lib/api-client";
import { env } from "@/config/env";

export interface PaymentRefundResponse {
  order_id: number;
  payment_status: string;
  status: string;
  refund_id?: string | null;
}

export const paymentsAdminService = {
  async refund(orderId: number, stepUpToken: string): Promise<PaymentRefundResponse> {
    if (env.USE_MOCK) {
      return {
        order_id: orderId,
        payment_status: "refunded",
        status: "cancelled",
        refund_id: `mock-refund-${orderId}`,
      };
    }
    const { data } = await apiClient.post<PaymentRefundResponse>(
      "/payments/refund",
      { order_id: orderId },
      withStepUp(stepUpToken),
    );
    return data;
  },
};
