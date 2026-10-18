import { describe, expect, it } from "vitest";
import { calculateProductDiscount } from "./discount-pricing";

describe("calculateProductDiscount", () => {
  it.each([
    ["3203-1506", "47100000", "40035000.00"],
    ["S3-2824", "53400000", "45390000.00"],
  ])("calculates the owner-approved 15%% for %s", (_sku, original, expected) => {
    expect(calculateProductDiscount(original, "", "15")).toEqual({
      basePrice: expected,
      originalPrice: `${original}.00`,
    });
  });

  it("uses the original list price instead of stacking a second discount", () => {
    expect(calculateProductDiscount("900", "1000", "15")).toEqual({
      basePrice: "850.00",
      originalPrice: "1000.00",
    });
  });

  it("rounds half up at two decimal places", () => {
    expect(calculateProductDiscount("1.01", "", "50")).toEqual({
      basePrice: "0.51",
      originalPrice: "1.01",
    });
  });

  it.each(["0", "100", "-15", "15.123", "foo", ""])
    ("rejects an invalid percentage (%s)", (percent) => {
      expect(() => calculateProductDiscount("1000", "", percent)).toThrow();
    });

  it("rejects a corrupt original_price rather than re-discounting the sale price", () => {
    expect(() => calculateProductDiscount("53400000", "10", "15"))
      .toThrow(/ناسازگار/);
  });

  it("rejects missing or invalid reference prices", () => {
    expect(() => calculateProductDiscount("", "", "15")).toThrow();
    expect(() => calculateProductDiscount("1e6", "", "15")).toThrow();
    expect(() => calculateProductDiscount("0", "", "15")).toThrow();
    expect(() => calculateProductDiscount("100", "100", "15")).toThrow();
  });
});
