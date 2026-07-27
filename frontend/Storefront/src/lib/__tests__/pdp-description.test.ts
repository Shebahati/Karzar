import { describe, expect, it } from "vitest";
import {
  collectSpecFingerprints,
  filterEditorialDescription,
  hasRenderableSpecs,
  normalizeSpecText,
} from "@/lib/pdp-description";
import type { ProductSpecifications } from "@/types/product";

const sampleSpecs: ProductSpecifications = {
  technical_specs: [
    { key: "بازه اندازه‌گیری", value: "۰–۱۵۰ mm" },
    { key: "دقت", value: "۰٫۰۱ mm" },
  ],
  dimensions: [{ key: "طول", value: "230" }],
  features: { waterproof: true, battery_type: "SR44" },
};

describe("normalizeSpecText", () => {
  it("collapses Persian digits and separators", () => {
    expect(normalizeSpecText("دقت: ۰٫۰۱ mm")).toBe(
      normalizeSpecText("دقت 0.01 mm"),
    );
  });
});

describe("collectSpecFingerprints", () => {
  it("includes key/value pairs from technical specs", () => {
    const fps = collectSpecFingerprints(sampleSpecs);
    expect(fps.has(normalizeSpecText("بازه اندازه‌گیری ۰–۱۵۰ mm"))).toBe(true);
    expect(fps.has(normalizeSpecText("دقت: ۰٫۰۱ mm"))).toBe(true);
  });
});

describe("filterEditorialDescription", () => {
  it("returns null when description only echoes short_description", () => {
    const short = "کولیس دیجیتال دقیق برای کارگاه";
    expect(filterEditorialDescription(short, sampleSpecs, short)).toBeNull();
  });

  it("strips bullet lines that duplicate SoT specs", () => {
    const long = [
      "این کولیس برای اندازه‌گیری عمومی در خط تولید مناسب است.",
      "• بازه اندازه‌گیری: ۰–۱۵۰ mm",
      "- دقت: ۰٫۰۱ mm",
      "طول: 230 mm",
      "بسته‌بندی استاندارد کارخانه را همراه دارد.",
    ].join("\n");

    const result = filterEditorialDescription(long, sampleSpecs, null);
    expect(result).toContain("این کولیس برای اندازه‌گیری عمومی");
    expect(result).toContain("بسته‌بندی استاندارد");
    expect(result).not.toMatch(/بازه اندازه‌گیری/);
    expect(result).not.toMatch(/دقت/);
    expect(result).not.toMatch(/طول/);
  });

  it("keeps prose that merely mentions a spec word in a sentence", () => {
    const long =
      "دقت این مدل برای کارگاه‌های عمومی کافی است و نیازی به آزمایشگاه مترولوژی ندارد.";
    expect(filterEditorialDescription(long, sampleSpecs, null)).toBe(long);
  });

  it("returns null when every line was a spec dump", () => {
    const long = ["بازه اندازه‌گیری: ۰–۱۵۰ mm", "دقت: ۰٫۰۱ mm"].join("\n");
    expect(filterEditorialDescription(long, sampleSpecs, null)).toBeNull();
  });
});

describe("hasRenderableSpecs", () => {
  it("detects empty vs populated specs", () => {
    expect(hasRenderableSpecs(sampleSpecs)).toBe(true);
    expect(
      hasRenderableSpecs({
        technical_specs: [],
        dimensions: [],
        features: {},
      }),
    ).toBe(false);
  });
});
