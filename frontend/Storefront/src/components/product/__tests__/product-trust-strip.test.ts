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
  it("omits authenticity when isOriginal is false", () => {
    const items = buildPdpStripTrustItems({ isOriginal: false });
    expect(items.map((i) => i.key)).toEqual([
      "return",
      "shipping",
      "support",
      "payment",
    ]);
    expect(items.find((i) => i.key === "authenticity")).toBeUndefined();
    expect(items.find((i) => i.key === "return")?.title).toBe("امکان مرجوعی");
    expect(items.find((i) => i.key === "return")?.desc).toBe(
      "طبق شرایط و موارد مشمول",
    );
  });

  it("shows authenticity only when isOriginal is true", () => {
    const items = buildPdpStripTrustItems({ isOriginal: true });
    expect(items.map((i) => i.key)).toEqual([
      "authenticity",
      "return",
      "shipping",
      "support",
      "payment",
    ]);
    expect(items.find((i) => i.key === "authenticity")?.desc).toBe(
      "کالای اصلی",
    );
    expect(JSON.stringify(items)).not.toContain("نمایندگی رسمی");
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

  it("does not add authenticity chip when isOriginal is false", () => {
    const items = buildPdpTrustItems({
      warrantyText: null,
      isOriginal: false,
    });
    expect(items.map((i) => i.key)).not.toContain("authenticity");
  });
});
