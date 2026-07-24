import { apiClient } from "@/lib/api-client";
import { getMockApi } from "@/lib/get-mock-api";
import { env } from "@/config/env";
import { ORDER_STATUS_LABELS } from "@/lib/constants";
import {
  clearPaymentIdempotencyKey,
  getOrCreateScopedIdempotencyKey,
  paymentIdempotencyStorageKey,
} from "@/lib/idempotency";
import type {
  PaymentInitPayload,
  PaymentInitBackendResponse,
  PaymentInitResponse,
  PaymentVerifyPayload,
  PaymentVerifyBackendResponse,
  PaymentVerifyResponse,
} from "@/types/payment";
import type { OrderStatus } from "@/types/order";

function mapVerifyResponse(
  backend: PaymentVerifyBackendResponse,
  trackingCode: string,
  success: boolean,
  message: string,
): PaymentVerifyResponse {
  return {
    success,
    order_id: backend.order_id,
    tracking_code: trackingCode,
    status: backend.status,
    status_label: ORDER_STATUS_LABELS[backend.status as OrderStatus] ?? backend.status,
    ref_id: backend.ref_id,
    message,
  };
}

export const paymentService = {
  async init(payload: PaymentInitPayload): Promise<PaymentInitResponse> {
    if (env.USE_MOCK) return (await getMockApi()).initPayment(payload);
    const storageKey = paymentIdempotencyStorageKey(payload.order_id);
    const idempotencyKey = getOrCreateScopedIdempotencyKey(storageKey);
    try {
      const { data } = await apiClient.post<PaymentInitBackendResponse>(
        "/payments/init",
        payload,
        { headers: { "Idempotency-Key": idempotencyKey } },
      );
      // Keep key until payment is verified / abandoned — retries must reuse it.
      return data;
    } catch (err) {
      throw err;
    }
  },

  async verify(
    payload: PaymentVerifyPayload & { tracking_code?: string },
  ): Promise<PaymentVerifyResponse> {
    if (env.USE_MOCK) return (await getMockApi()).verifyPayment(payload);

    const body: { authority: string; status?: string; order_id?: number } = {
      authority: payload.authority,
      status: payload.status,
    };
    if (payload.order_id != null) {
      body.order_id = payload.order_id;
    }

    const { data } = await apiClient.post<PaymentVerifyBackendResponse>(
      "/payments/verify",
      body,
    );

    const gatewayOk = !payload.status || payload.status.toUpperCase() === "OK";
    const ok =
      gatewayOk &&
      (data.payment_status === "paid" ||
        data.status === "paid" ||
        data.payment_status === "verified");

    if (ok && payload.order_id != null) {
      clearPaymentIdempotencyKey(payload.order_id);
    } else if (ok) {
      clearPaymentIdempotencyKey(data.order_id);
    }

    return mapVerifyResponse(
      data,
      payload.tracking_code ?? data.tracking_code ?? "",
      ok,
      ok ? "پرداخت با موفقیت انجام شد." : "پرداخت ناموفق بود.",
    );
  },
};
