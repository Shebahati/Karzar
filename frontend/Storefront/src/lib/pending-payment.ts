/** Persist pending payment identity across tab close (local) and same-tab (session). */

import { PAYMENT_PENDING_ORDER_KEY } from "@/lib/constants";

export interface PendingPayment {
  order_id: number;
  tracking_code: string;
  /** Epoch ms — discard after this time. */
  expires_at: number;
  /**
   * Purchase-cart owner captured at checkout/payment initiation.
   * Missing/invalid on legacy records → fail closed for local cart cleanup.
   */
  customer_id?: number;
}

const TTL_MS = 24 * 60 * 60 * 1000;

function isValid(pending: PendingPayment | null): pending is PendingPayment {
  return Boolean(
    pending &&
      Number.isFinite(pending.order_id) &&
      pending.order_id > 0 &&
      pending.tracking_code &&
      pending.expires_at > Date.now(),
  );
}

export function pendingPaymentHasOwner(
  pending: PendingPayment | null,
): pending is PendingPayment & { customer_id: number } {
  return Boolean(
    pending &&
      typeof pending.customer_id === "number" &&
      Number.isFinite(pending.customer_id) &&
      pending.customer_id > 0,
  );
}

function parse(raw: string | null): PendingPayment | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as PendingPayment;
    return isValid(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

/**
 * Persist pending payment with the checkout cart owner.
 * Retry paths must pass the same customer_id (or use preserveOwnerFromExisting).
 */
export function savePendingPayment(
  orderId: number,
  trackingCode: string,
  customerId: number,
): void {
  if (typeof window === "undefined") return;
  if (!Number.isFinite(customerId) || customerId <= 0) return;
  const pending: PendingPayment = {
    order_id: orderId,
    tracking_code: trackingCode,
    expires_at: Date.now() + TTL_MS,
    customer_id: customerId,
  };
  const raw = JSON.stringify(pending);
  try {
    window.sessionStorage.setItem(PAYMENT_PENDING_ORDER_KEY, raw);
  } catch {
    /* ignore */
  }
  try {
    window.localStorage.setItem(PAYMENT_PENDING_ORDER_KEY, raw);
  } catch {
    /* ignore */
  }
}

/**
 * Retry payment: keep the original owner when the same order is still pending.
 */
export function savePendingPaymentPreservingOwner(
  orderId: number,
  trackingCode: string,
  customerIdFallback: number | null,
): boolean {
  const existing = readPendingPayment();
  const owner =
    existing &&
    existing.order_id === orderId &&
    pendingPaymentHasOwner(existing)
      ? existing.customer_id
      : customerIdFallback;
  if (owner == null || !Number.isFinite(owner) || owner <= 0) return false;
  savePendingPayment(orderId, trackingCode, owner);
  return true;
}

export function readPendingPayment(): PendingPayment | null {
  if (typeof window === "undefined") return null;
  let pending: PendingPayment | null = null;
  try {
    pending = parse(window.sessionStorage.getItem(PAYMENT_PENDING_ORDER_KEY));
  } catch {
    pending = null;
  }
  if (pending) return pending;
  try {
    pending = parse(window.localStorage.getItem(PAYMENT_PENDING_ORDER_KEY));
  } catch {
    pending = null;
  }
  return pending;
}

export function clearPendingPayment(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(PAYMENT_PENDING_ORDER_KEY);
  } catch {
    /* ignore */
  }
  try {
    window.localStorage.removeItem(PAYMENT_PENDING_ORDER_KEY);
  } catch {
    /* ignore */
  }
}

/** Clear pending payment only when it still matches the expected order identity. */
export function clearPendingPaymentIfMatches(expected: {
  order_id: number;
  tracking_code: string;
}): boolean {
  const current = readPendingPayment();
  if (
    !current ||
    current.order_id !== expected.order_id ||
    current.tracking_code !== expected.tracking_code
  ) {
    return false;
  }
  clearPendingPayment();
  return true;
}
