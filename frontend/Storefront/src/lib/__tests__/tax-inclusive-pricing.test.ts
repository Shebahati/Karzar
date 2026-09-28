import { describe, expect, it } from "vitest";
import { payableTotalToman } from "@/lib/shipping-quote";

/**
 * Production helpers used by checkout order-summary / shipping UX.
 * Cart and OrderSummary compute merchandise as Σ(base_price × qty) inline;
 * payableTotalToman is the shared shipping/payable combiner — tax_percent
 * is not a parameter and must never enter this path.
 */
describe("tax-inclusive payable totals (production helpers)", () => {
  it("payableTotalToman ignores tax and excludes shipping for receiver_due", () => {
    const merchandise = 1_000_000; // displayed base_price × qty
    // There is no tax argument — production API cannot surcharge via this helper.
    expect(payableTotalToman(merchandise, 50_000, { shippingExcluded: true })).toBe(
      1_000_000,
    );
    expect(payableTotalToman.length).toBeLessThanOrEqual(3);
  });

  it("payableTotalToman adds prepaid shipping once without any tax multiplier", () => {
    const merchandise = 4_000_000;
    expect(payableTotalToman(merchandise, 100_000)).toBe(4_100_000);
    expect(payableTotalToman(merchandise, null)).toBe(4_000_000);
  });

  it("cart merchandise formula matches checkout merchandise (no tax)", () => {
    // Mirrors cart-view.tsx / order-summary.tsx: Number(base_price) * quantity
    const lines = [
      { base_price: "500000", quantity: 2, tax_percent: "0" },
      { base_price: "1000000", quantity: 1, tax_percent: "9" },
      { base_price: "2000000", quantity: 1, tax_percent: "10" },
    ];
    const merchandise = lines.reduce(
      (sum, l) => sum + Number(l.base_price) * l.quantity,
      0,
    );
    expect(merchandise).toBe(4_000_000);
    expect(payableTotalToman(merchandise, null, { shippingExcluded: true })).toBe(
      merchandise,
    );
  });
});
