import { describe, expect, it } from "vitest";
import {
  canSubmitPurchaseShipping,
  isQuoteExpired,
  payableTotalToman,
} from "@/lib/shipping-quote";

describe("shipping quote helpers", () => {
  it("adds shipping once to the payable total", () => {
    expect(payableTotalToman(100000, 17000)).toBe(117000);
    expect(payableTotalToman(100000, null)).toBe(100000);
  });

  it("treats past expires_at as expired", () => {
    expect(isQuoteExpired("2020-01-01T00:00:00.000Z", Date.parse("2026-09-10"))).toBe(true);
    expect(isQuoteExpired("2099-01-01T00:00:00.000Z", Date.parse("2026-09-10"))).toBe(false);
  });

  it("blocks purchase until a live quote exists when Postex is on", () => {
    expect(
      canSubmitPurchaseShipping({
        postexEnabled: true,
        quoteToken: null,
        expiresAt: null,
        shippingUnavailable: false,
      }),
    ).toBe(false);
    expect(
      canSubmitPurchaseShipping({
        postexEnabled: true,
        quoteToken: "tok",
        expiresAt: "2099-01-01T00:00:00.000Z",
        shippingUnavailable: false,
      }),
    ).toBe(true);
    expect(
      canSubmitPurchaseShipping({
        postexEnabled: true,
        quoteToken: "tok",
        expiresAt: "2099-01-01T00:00:00.000Z",
        shippingUnavailable: true,
      }),
    ).toBe(false);
    expect(
      canSubmitPurchaseShipping({
        postexEnabled: false,
        quoteToken: null,
        expiresAt: null,
        shippingUnavailable: false,
      }),
    ).toBe(true);
  });
});
