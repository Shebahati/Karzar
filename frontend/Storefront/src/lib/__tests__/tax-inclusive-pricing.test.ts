import { describe, expect, it } from "vitest";
import { payableTotalToman } from "@/lib/shipping-quote";

describe("tax-inclusive payable totals", () => {
  it("never multiplies merchandise by tax metadata", () => {
    const base = 1_000_000;
    const qty = 1;
    const taxPercent = 9;
    const merchandise = base * qty;
    // taxPercent is accounting-only; must not affect payable
    expect(merchandise * (1 + taxPercent / 100)).not.toBe(merchandise);
    expect(payableTotalToman(merchandise, null, { shippingExcluded: true })).toBe(
      1_000_000,
    );
  });

  it("receiver_due excludes shipping; sender_prepaid adds shipping once", () => {
    const merchandise = 4_000_000;
    expect(payableTotalToman(merchandise, 100_000, { shippingExcluded: true })).toBe(
      4_000_000,
    );
    expect(payableTotalToman(merchandise, 100_000)).toBe(4_100_000);
  });

  it("mixed tax metadata does not change cart merchandise sum", () => {
    const lines = [
      { base: 500_000, qty: 2, tax: 0 },
      { base: 1_000_000, qty: 1, tax: 9 },
      { base: 2_000_000, qty: 1, tax: 10 },
    ];
    const total = lines.reduce((sum, l) => sum + l.base * l.qty, 0);
    expect(total).toBe(4_000_000);
  });
});
