import { describe, expect, it } from "vitest";

import {
  isValidPostalTrackingCode,
  normalizeTrackingCodeInput,
} from "../ship-tracking-validation";

describe("ship tracking validation", () => {
  it("trims whitespace and preserves leading zeros", () => {
    expect(normalizeTrackingCodeInput("  001234567890  ")).toBe("001234567890");
  });

  it("requires minimum length for postal-style tracking", () => {
    expect(isValidPostalTrackingCode("123456789")).toBe(false);
    expect(isValidPostalTrackingCode("1234567890")).toBe(true);
    expect(isValidPostalTrackingCode("001234567890")).toBe(true);
  });
});
