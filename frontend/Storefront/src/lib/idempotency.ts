/** Stable Idempotency-Key helpers for checkout / payment retries. */

import { createIdempotencyKey } from "@/lib/api-client";
import type { CheckoutPayload } from "@/types/checkout";

const CHECKOUT_PREFIX = "karzar.idem.checkout:";
const PAYMENT_PREFIX = "karzar.idem.payment:";

function stableHash(input: string): string {
  // FNV-1a 32-bit — deterministic, short, good enough for sessionStorage keys.
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16);
}

export function checkoutIdempotencyScope(payload: CheckoutPayload): string {
  const lines = [...payload.items]
    .map((line) => `${line.product_id}:${line.quantity}`)
    .sort()
    .join(",");
  const shipping = payload.shipping
    ? [
        payload.shipping.province,
        payload.shipping.city,
        payload.shipping.postal_code,
        payload.shipping.address_line,
      ].join("|")
    : "";
  const raw = [
    payload.mode,
    payload.customer.phone,
    payload.customer.full_name,
    payload.company_name ?? "",
    payload.note ?? "",
    lines,
    shipping,
  ].join("::");
  return stableHash(raw);
}

function readKey(storageKey: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(storageKey);
  } catch {
    return null;
  }
}

function writeKey(storageKey: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(storageKey, value);
  } catch {
    /* ignore quota / private mode */
  }
}

function removeKey(storageKey: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(storageKey);
  } catch {
    /* ignore */
  }
}

/** Return existing key for scope, or create and persist a new one. */
export function getOrCreateScopedIdempotencyKey(storageKey: string): string {
  const existing = readKey(storageKey);
  if (existing) return existing;
  const key = createIdempotencyKey();
  writeKey(storageKey, key);
  return key;
}

export function checkoutIdempotencyStorageKey(payload: CheckoutPayload): string {
  return `${CHECKOUT_PREFIX}${checkoutIdempotencyScope(payload)}`;
}

export function paymentIdempotencyStorageKey(orderId: number): string {
  return `${PAYMENT_PREFIX}${orderId}`;
}

export function clearCheckoutIdempotencyKey(payload: CheckoutPayload): void {
  removeKey(checkoutIdempotencyStorageKey(payload));
}

export function clearPaymentIdempotencyKey(orderId: number): void {
  removeKey(paymentIdempotencyStorageKey(orderId));
}
