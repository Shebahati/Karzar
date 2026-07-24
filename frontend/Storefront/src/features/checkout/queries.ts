"use client";

import { useMutation } from "@tanstack/react-query";
import { checkoutService } from "@/services/checkout";
import { paymentService } from "@/services/payments";
import type { CheckoutPayload, CheckoutResponse } from "@/types/checkout";
import type { ContactValues } from "@/lib/validation";
import type { PaymentInitPayload, PaymentInitResponse } from "@/types/payment";

export function useSubmitCheckout() {
  return useMutation<CheckoutResponse, Error, CheckoutPayload>({
    mutationFn: (payload) => checkoutService.submit(payload),
  });
}

export function useInitPayment() {
  return useMutation<PaymentInitResponse, Error, PaymentInitPayload>({
    mutationFn: (payload) => paymentService.init(payload),
  });
}

export function useSubmitContact() {
  return useMutation<{ ok: true; ticket: string }, Error, ContactValues>({
    mutationFn: (payload) => checkoutService.contact(payload),
  });
}
