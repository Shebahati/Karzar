import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearPendingPayment,
  readPendingPayment,
  savePendingPayment,
} from "@/lib/pending-payment";
import { PAYMENT_PENDING_ORDER_KEY } from "@/lib/constants";

describe("pending-payment", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.useRealTimers();
  });

  it("writes to both session and local storage", () => {
    savePendingPayment(7, "KZ-100");
    const fromSession = JSON.parse(sessionStorage.getItem(PAYMENT_PENDING_ORDER_KEY)!);
    const fromLocal = JSON.parse(localStorage.getItem(PAYMENT_PENDING_ORDER_KEY)!);
    expect(fromSession.order_id).toBe(7);
    expect(fromLocal.tracking_code).toBe("KZ-100");
  });

  it("prefers session over local on read", () => {
    localStorage.setItem(
      PAYMENT_PENDING_ORDER_KEY,
      JSON.stringify({ order_id: 1, tracking_code: "LOCAL", expires_at: Date.now() + 60_000 }),
    );
    sessionStorage.setItem(
      PAYMENT_PENDING_ORDER_KEY,
      JSON.stringify({ order_id: 2, tracking_code: "SESSION", expires_at: Date.now() + 60_000 }),
    );
    expect(readPendingPayment()?.tracking_code).toBe("SESSION");
  });

  it("falls back to local when session is empty", () => {
    localStorage.setItem(
      PAYMENT_PENDING_ORDER_KEY,
      JSON.stringify({ order_id: 3, tracking_code: "LOCAL-ONLY", expires_at: Date.now() + 60_000 }),
    );
    expect(readPendingPayment()?.order_id).toBe(3);
  });

  it("ignores expired entries", () => {
    sessionStorage.setItem(
      PAYMENT_PENDING_ORDER_KEY,
      JSON.stringify({ order_id: 9, tracking_code: "OLD", expires_at: Date.now() - 1 }),
    );
    expect(readPendingPayment()).toBeNull();
  });

  it("clears both stores", () => {
    savePendingPayment(1, "KZ-1");
    clearPendingPayment();
    expect(sessionStorage.getItem(PAYMENT_PENDING_ORDER_KEY)).toBeNull();
    expect(localStorage.getItem(PAYMENT_PENDING_ORDER_KEY)).toBeNull();
  });
});
