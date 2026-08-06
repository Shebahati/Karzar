import { describe, expect, it } from "vitest";
import { buildPdpTrustItems } from "@/components/product/product-trust-strip";

describe("buildPdpTrustItems", () => {
  it("always includes authenticity and return", () => {
    const items = buildPdpTrustItems({ warrantyText: null, isOriginal: false });
    expect(items.map((i) => i.key)).toEqual(["authenticity", "return"]);
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
    ]);
    expect(items.find((i) => i.key === "warranty")?.title).toBe(
      "۱۸ ماه گارانتی شرکتی",
    );
  });
});
