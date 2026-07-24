import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  checkoutIdempotencyScope,
  checkoutIdempotencyStorageKey,
  getOrCreateScopedIdempotencyKey,
  paymentIdempotencyStorageKey,
} from "@/lib/idempotency";
import type { CheckoutPayload } from "@/types/checkout";

const basePayload = (): CheckoutPayload => ({
  mode: "purchase",
  customer: { full_name: "علی", phone: "09120000000", is_guest: false },
  items: [
    { product_id: 2, quantity: 1 },
    { product_id: 1, quantity: 3 },
  ],
  shipping: {
    province: "تهران",
    city: "تهران",
    postal_code: "1234567890",
    address_line: "خیابان ولیعصر، پلاک ۱۲۳",
  },
});

describe("checkoutIdempotencyScope", () => {
  it("is stable across item order", () => {
    const a = basePayload();
    const b = basePayload();
    b.items = [...a.items].reverse();
    expect(checkoutIdempotencyScope(a)).toBe(checkoutIdempotencyScope(b));
  });

  it("changes when quantity changes", () => {
    const a = basePayload();
    const b = basePayload();
    b.items = [{ product_id: 1, quantity: 99 }, { product_id: 2, quantity: 1 }];
    expect(checkoutIdempotencyScope(a)).not.toBe(checkoutIdempotencyScope(b));
  });

  it("builds prefixed storage keys", () => {
    const payload = basePayload();
    expect(checkoutIdempotencyStorageKey(payload)).toMatch(/^karzar\.idem\.checkout:/);
    expect(paymentIdempotencyStorageKey(42)).toBe("karzar.idem.payment:42");
  });
});

describe("getOrCreateScopedIdempotencyKey", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("reuses the same key for the same storage slot", () => {
    const first = getOrCreateScopedIdempotencyKey("test-scope");
    const second = getOrCreateScopedIdempotencyKey("test-scope");
    expect(first).toBe(second);
    expect(sessionStorage.getItem("test-scope")).toBe(first);
  });
});
