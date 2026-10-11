import { apiClient, withStepUp } from "@/lib/api-client";
import { env } from "@/config/env";

export type PaymentRefundMode = "automated" | "external_confirmation";

export interface PaymentCapabilities {
  provider: string;
  automated_refund_supported: boolean;
  external_refund_confirmation_supported: boolean;
  refund_mode: PaymentRefundMode;
}

export interface PaymentRefundResponse {
  order_id: number;
  payment_status: string;
  status: string;
  refund_id?: string | null;
}

export interface PaymentExternalRefundConfirmationResponse {
  order_id: number;
  payment_status: string;
  status: string;
  refund_id: string;
  cancelled: boolean;
  reconciliation_required: boolean;
}

export interface PaymentExternalRefundConfirmationRequest {
  order_id: number;
  external_reference: string;
  evidence_note?: string;
}

export const paymentsAdminService = {
  async getCapabilities(): Promise<PaymentCapabilities> {
    if (env.USE_MOCK) {
      return {
        provider: "mock",
        automated_refund_supported: true,
        external_refund_confirmation_supported: false,
        refund_mode: "automated",
      };
    }
    const { data } = await apiClient.get<PaymentCapabilities>("/payments/capabilities");
    return data;
  },

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

  async confirmExternalRefund(
    payload: PaymentExternalRefundConfirmationRequest,
    stepUpToken: string,
  ): Promise<PaymentExternalRefundConfirmationResponse> {
    if (env.USE_MOCK) {
      return {
        order_id: payload.order_id,
        payment_status: "refunded",
        status: "cancelled",
        refund_id: payload.external_reference,
        cancelled: true,
        reconciliation_required: false,
      };
    }
    const { data } = await apiClient.post<PaymentExternalRefundConfirmationResponse>(
      "/payments/refund/external-confirmation",
      payload,
      withStepUp(stepUpToken),
    );
    return data;
  },
};
