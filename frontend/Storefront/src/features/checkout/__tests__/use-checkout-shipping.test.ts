import { describe, expect, it } from "vitest";
import { methodOptionSubtitle } from "@/features/checkout/use-checkout-shipping";

describe("methodOptionSubtitle", () => {
  it("uses Tehran Express courier copy", () => {
    expect(methodOptionSubtitle("tehran_express")).toContain("پیک");
  });

  it("uses Tipax receiver copy", () => {
    expect(methodOptionSubtitle("tipax_standard")).toContain("گیرنده");
  });
});
