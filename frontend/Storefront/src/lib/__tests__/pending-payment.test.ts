import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearPendingPayment,
  clearPendingPaymentIfMatches,
  pendingPaymentHasOwner,
  readPendingPayment,
  savePendingPayment,
  savePendingPaymentPreservingOwner,
} from "@/lib/pending-payment";
import { PAYMENT_PENDING_ORDER_KEY } from "@/lib/constants";

describe("pending-payment", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.useRealTimers();
  });

  it("writes to both session and local storage with customer owner", () => {
    savePendingPayment(7, "KZ-100", 1);
    const fromSession = JSON.parse(sessionStorage.getItem(PAYMENT_PENDING_ORDER_KEY)!);
    const fromLocal = JSON.parse(localStorage.getItem(PAYMENT_PENDING_ORDER_KEY)!);
    expect(fromSession.order_id).toBe(7);
    expect(fromLocal.tracking_code).toBe("KZ-100");
    expect(fromSession.customer_id).toBe(1);
    expect(pendingPaymentHasOwner(readPendingPayment())).toBe(true);
  });

  it("prefers session over local on read", () => {
    localStorage.setItem(
      PAYMENT_PENDING_ORDER_KEY,
      JSON.stringify({
        order_id: 1,
        tracking_code: "LOCAL",
        expires_at: Date.now() + 60_000,
        customer_id: 1,
      }),
    );
    sessionStorage.setItem(
      PAYMENT_PENDING_ORDER_KEY,
      JSON.stringify({
        order_id: 2,
        tracking_code: "SESSION",
        expires_at: Date.now() + 60_000,
        customer_id: 2,
      }),
    );
    expect(readPendingPayment()?.tracking_code).toBe("SESSION");
  });

  it("falls back to local when session is empty", () => {
    localStorage.setItem(
      PAYMENT_PENDING_ORDER_KEY,
      JSON.stringify({
        order_id: 3,
        tracking_code: "LOCAL-ONLY",
        expires_at: Date.now() + 60_000,
        customer_id: 3,
      }),
    );
    expect(readPendingPayment()?.order_id).toBe(3);
  });

  it("ignores expired entries", () => {
    sessionStorage.setItem(
      PAYMENT_PENDING_ORDER_KEY,
      JSON.stringify({
        order_id: 9,
        tracking_code: "OLD",
        expires_at: Date.now() - 1,
        customer_id: 1,
      }),
    );
    expect(readPendingPayment()).toBeNull();
  });

  it("legacy pending without customer_id is readable but owner-unsafe", () => {
    sessionStorage.setItem(
      PAYMENT_PENDING_ORDER_KEY,
      JSON.stringify({
        order_id: 4,
        tracking_code: "LEGACY",
        expires_at: Date.now() + 60_000,
      }),
    );
    const pending = readPendingPayment();
    expect(pending?.tracking_code).toBe("LEGACY");
    expect(pendingPaymentHasOwner(pending)).toBe(false);
  });

  it("clears both stores", () => {
    savePendingPayment(1, "KZ-1", 1);
    clearPendingPayment();
    expect(sessionStorage.getItem(PAYMENT_PENDING_ORDER_KEY)).toBeNull();
    expect(localStorage.getItem(PAYMENT_PENDING_ORDER_KEY)).toBeNull();
  });

  it("compare-and-clear only retires the matching pending record", () => {
    savePendingPayment(1, "KZ-1", 1);
    expect(clearPendingPaymentIfMatches({ order_id: 9, tracking_code: "KZ-1" })).toBe(false);
    expect(readPendingPayment()?.order_id).toBe(1);
    expect(clearPendingPaymentIfMatches({ order_id: 1, tracking_code: "KZ-1" })).toBe(true);
    expect(readPendingPayment()).toBeNull();
  });

  it("preserving owner keeps original customer_id on retry", () => {
    savePendingPayment(10, "KZ-10", 1);
    expect(savePendingPaymentPreservingOwner(10, "KZ-10", 99)).toBe(true);
    expect(readPendingPayment()?.customer_id).toBe(1);
  });
});
