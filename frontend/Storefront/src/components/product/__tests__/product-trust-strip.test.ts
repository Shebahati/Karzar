import { describe, expect, it } from "vitest";
import {
  buildPdpBuyCardTrust,
  buildPdpStripTrustItems,
  buildPdpTrustItems,
} from "@/components/product/product-trust-strip";

describe("buildPdpBuyCardTrust", () => {
  it("returns empty when warranty is missing", () => {
    expect(buildPdpBuyCardTrust({ warrantyText: null })).toEqual([]);
    expect(buildPdpBuyCardTrust({ warrantyText: "  " })).toEqual([]);
  });

  it("returns product warranty copy without inventing extras", () => {
    const items = buildPdpBuyCardTrust({
      warrantyText: "۱۸ ماه گارانتی شرکتی",
    });
    expect(items.map((i) => i.key)).toEqual(["warranty"]);
    expect(items[0]?.title).toBe("۱۸ ماه گارانتی شرکتی");
    expect(items[0]?.desc).toBe("شرایط گارانتی");
  });
});

describe("buildPdpStripTrustItems", () => {
  it("includes authenticity, return, and service cues", () => {
    const items = buildPdpStripTrustItems({ isOriginal: false });
    expect(items.map((i) => i.key)).toEqual([
      "authenticity",
      "return",
      "shipping",
      "support",
      "payment",
    ]);
    expect(items.find((i) => i.key === "authenticity")?.desc).toBe(
      "نمایندگی رسمی",
    );
  });

  it("uses original goods copy when isOriginal", () => {
    const items = buildPdpStripTrustItems({ isOriginal: true });
    expect(items.find((i) => i.key === "authenticity")?.desc).toBe(
      "کالای اصلی",
    );
  });
});

describe("buildPdpTrustItems (compat)", () => {
  it("merges strip cues with optional warranty", () => {
    const items = buildPdpTrustItems({
      warrantyText: "۱۸ ماه گارانتی شرکتی",
      isOriginal: true,
    });
    expect(items.map((i) => i.key)).toEqual([
      "authenticity",
      "return",
      "shipping",
      "support",
      "payment",
      "warranty",
    ]);
  });
});
