import { describe, expect, it } from "vitest";
import { isAllowedPaymentUrl } from "@/lib/payment-url";

describe("isAllowedPaymentUrl", () => {
  it("allows Zarinpal StartPay https", () => {
    expect(
      isAllowedPaymentUrl("https://www.zarinpal.com/pg/StartPay/A000111"),
    ).toBe(true);
  });

  it("rejects arbitrary https hosts", () => {
    expect(isAllowedPaymentUrl("https://evil.example/phish")).toBe(false);
  });

  it("rejects javascript: and relative urls", () => {
    expect(isAllowedPaymentUrl("javascript:alert(1)")).toBe(false);
    expect(isAllowedPaymentUrl("/checkout/payment/callback")).toBe(false);
  });

  it("allows localhost http for mock", () => {
    expect(
      isAllowedPaymentUrl(
        "http://localhost:8000/api/v1/payments/callback?Authority=MOCK-1&Status=OK",
      ),
    ).toBe(true);
  });
});
