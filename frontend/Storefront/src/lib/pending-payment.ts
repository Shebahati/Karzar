/** Persist pending payment identity across tab close (local) and same-tab (session). */

import { PAYMENT_PENDING_ORDER_KEY } from "@/lib/constants";

export interface PendingPayment {
  order_id: number;
  tracking_code: string;
  /** Epoch ms — discard after this time. */
  expires_at: number;
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

function parse(raw: string | null): PendingPayment | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as PendingPayment;
    return isValid(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function savePendingPayment(orderId: number, trackingCode: string): void {
  if (typeof window === "undefined") return;
  const pending: PendingPayment = {
    order_id: orderId,
    tracking_code: trackingCode,
    expires_at: Date.now() + TTL_MS,
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
