import { apiClient } from "@/lib/api-client";
import { getMockApi } from "@/lib/get-mock-api";
import { env } from "@/config/env";
import {
  checkoutIdempotencyStorageKey,
  clearCheckoutIdempotencyKey,
  getOrCreateScopedIdempotencyKey,
} from "@/lib/idempotency";
import type { CheckoutPayload, CheckoutResponse } from "@/types/checkout";
import type { ContactValues } from "@/lib/validation";

export const checkoutService = {
  async submit(payload: CheckoutPayload): Promise<CheckoutResponse> {
    if (env.USE_MOCK) return (await getMockApi()).submitCheckout(payload);
    const storageKey = checkoutIdempotencyStorageKey(payload);
    const idempotencyKey = getOrCreateScopedIdempotencyKey(storageKey);
    try {
      const { data } = await apiClient.post<CheckoutResponse>("/checkout", payload, {
        headers: { "Idempotency-Key": idempotencyKey },
      });
      // Success: drop key so a brand-new checkout later gets a fresh key.
      clearCheckoutIdempotencyKey(payload);
      return data;
    } catch (err) {
      // Keep key on failure so retries reuse the same Idempotency-Key.
      throw err;
    }
  },

  async contact(payload: ContactValues): Promise<{ ok: true; ticket: string }> {
    if (env.USE_MOCK) return (await getMockApi()).submitContact(payload);
    const { data } = await apiClient.post<{ ok: true; ticket: string }>(
      "/contact",
      payload,
    );
    return data;
  },
};
