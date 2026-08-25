import { describe, expect, it } from "vitest";
import { isAllowedPaymentUrl } from "@/lib/payment-url";

describe("isAllowedPaymentUrl", () => {
  it("allows Zarinpal StartPay https", () => {
    expect(
      isAllowedPaymentUrl("https://www.zarinpal.com/pg/StartPay/A000111"),
    ).toBe(true);
  });

  it("allows SEP SendToken https", () => {
    expect(
      isAllowedPaymentUrl(
        "https://sep.shaparak.ir/OnlinePG/SendToken?token=abc123token",
      ),
    ).toBe(true);
  });

  it("rejects SEP over http", () => {
    expect(
      isAllowedPaymentUrl("http://sep.shaparak.ir/OnlinePG/SendToken?token=x"),
    ).toBe(false);
  });

  it("rejects lookalike SEP hosts and query-only mentions", () => {
    expect(isAllowedPaymentUrl("https://sep.shaparak.ir.evil.example/")).toBe(
      false,
    );
    expect(
      isAllowedPaymentUrl("https://evil.example/?next=sep.shaparak.ir"),
    ).toBe(false);
    expect(isAllowedPaymentUrl("https://evil-sep.shaparak.ir/pay")).toBe(false);
  });

  it("rejects arbitrary https hosts", () => {
    expect(isAllowedPaymentUrl("https://evil.example/phish")).toBe(false);
  });

  it("rejects javascript: and relative urls", () => {
    expect(isAllowedPaymentUrl("javascript:alert(1)")).toBe(false);
    expect(isAllowedPaymentUrl("data:text/html,hi")).toBe(false);
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
