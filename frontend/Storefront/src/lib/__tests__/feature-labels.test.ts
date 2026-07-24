import { describe, expect, it } from "vitest";
import { getFeatureLabelSync } from "@/lib/feature-labels";

describe("feature labels", () => {
  it("maps known technical_specs keys to Persian fallbacks", () => {
    expect(getFeatureLabelSync("grade")).toBe("گرید");
    expect(getFeatureLabelSync("coating")).toBe("پوشش");
    expect(getFeatureLabelSync("range")).toBe("بازه اندازه‌گیری");
    expect(getFeatureLabelSync("diameter_mm")).toBe("قطر (mm)");
  });

  it("falls back to the raw key when unknown", () => {
    expect(getFeatureLabelSync("totally_unknown_key_xyz")).toBe(
      "totally_unknown_key_xyz",
    );
  });
});
