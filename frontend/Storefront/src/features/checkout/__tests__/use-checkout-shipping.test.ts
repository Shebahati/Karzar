import { describe, expect, it } from "vitest";
import { methodOptionSubtitle } from "@/features/checkout/use-checkout-shipping";

describe("methodOptionSubtitle", () => {
  it("uses local courier copy for Tehran local methods", () => {
    expect(methodOptionSubtitle("tehran_express_3h")).toContain("پیک");
    expect(methodOptionSubtitle("tehran_motorcycle_48h")).toContain("پیک");
  });

  it("uses carrier receiver copy for nationwide methods", () => {
    expect(methodOptionSubtitle("tipax_standard")).toContain("گیرنده");
    expect(methodOptionSubtitle("post_pishtaz")).toContain("گیرنده");
  });
});
