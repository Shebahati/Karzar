import { describe, expect, it } from "vitest";
import { buildPdpTrustItems } from "@/components/product/product-trust-strip";

describe("buildPdpTrustItems", () => {
  it("always includes authenticity, return, and shipping", () => {
    const items = buildPdpTrustItems({ warrantyText: null, isOriginal: false });
    expect(items.map((i) => i.key)).toEqual([
      "authenticity",
      "return",
      "shipping",
    ]);
  });

  it("inserts product warranty when present without inventing copy", () => {
    const items = buildPdpTrustItems({
      warrantyText: "۱۸ ماه گارانتی شرکتی",
      isOriginal: true,
    });
    expect(items.map((i) => i.key)).toEqual([
      "authenticity",
      "warranty",
      "return",
      "shipping",
    ]);
    expect(items.find((i) => i.key === "warranty")?.title).toBe(
      "۱۸ ماه گارانتی شرکتی",
    );
  });
});
