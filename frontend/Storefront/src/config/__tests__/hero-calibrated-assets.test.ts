import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  HERO_CALIBRATED_ASSET_DIR,
  HERO_CAMPAIGN_FIVE_SLIDES,
  buildFiveHeroPublishedPack,
} from "@/config/hero-campaign-five";
import {
  CAMPAIGN_COMPACT_MAX_PX,
  CAMPAIGN_MOBILE_SOURCE_MAX_PX,
  DEFAULT_COMPACT_ASPECT,
  campaignMediaForSlide,
} from "@/lib/hero-campaign-layout";

const publicRoot = path.join(process.cwd(), "public");

const EXPECTED = [
  {
    id: "slide_h01_special_offers",
    desktop: "H01-special-offers-desktop-16x9.webp",
    mobile: "H01-special-offers-mobile-4x3.webp",
    href: "/catalog?on_sale=1",
  },
  {
    id: "slide_h02_measuring",
    desktop: "H02-measuring-tools-desktop-16x9.webp",
    mobile: "H02-measuring-tools-mobile-4x3.webp",
    href: "/categories/andaze-giri",
  },
  {
    id: "slide_h03_inserts",
    desktop: "H03-inserts-turning-tools-desktop-16x9.webp",
    mobile: "H03-inserts-turning-tools-mobile-4x3.webp",
    href: "/categories/insert",
    secondaryHref: "/categories/abzar-inserti",
  },
  {
    id: "slide_h04_endmills",
    desktop: "H04-end-mills-desktop-16x9.webp",
    mobile: "H04-end-mills-mobile-4x3.webp",
    href: "/categories/farz-angoshti",
  },
  {
    id: "slide_h05_machines",
    desktop: "H05-industrial-machines-desktop-16x9.webp",
    mobile: "H05-industrial-machines-mobile-4x3.webp",
    href: "/categories/dastgah-sanati",
  },
] as const;

function webpSize(filePath: string): { width: number; height: number } {
  const buf = readFileSync(filePath);
  if (buf.toString("ascii", 0, 4) !== "RIFF" || buf.toString("ascii", 8, 12) !== "WEBP") {
    throw new Error(`not a webp: ${filePath}`);
  }
  const chunk = buf.toString("ascii", 12, 16);
  if (chunk === "VP8X") {
    return {
      width: 1 + buf.readUIntLE(24, 3),
      height: 1 + buf.readUIntLE(27, 3),
    };
  }
  if (chunk === "VP8 ") {
    return {
      width: buf.readUInt16LE(26) & 0x3fff,
      height: buf.readUInt16LE(28) & 0x3fff,
    };
  }
  if (chunk === "VP8L") {
    const bits = buf.readUInt32LE(21);
    return {
      width: (bits & 0x3fff) + 1,
      height: ((bits >> 14) & 0x3fff) + 1,
    };
  }
  throw new Error(`unsupported webp chunk ${chunk} in ${filePath}`);
}

describe("calibrated five-hero assets", () => {
  it("keeps five slides in the approved order with H01 first", () => {
    expect(HERO_CAMPAIGN_FIVE_SLIDES.map((s) => s.id)).toEqual(EXPECTED.map((s) => s.id));
    expect(HERO_CAMPAIGN_FIVE_SLIDES[0]?.sortOrder).toBe(1);
    const pack = buildFiveHeroPublishedPack();
    expect(pack.slides.filter((s) => s.isActive)).toHaveLength(5);
    expect(pack.slides[0]?.id).toBe("slide_h01_special_offers");
    expect(pack.publishedAt).toBe("2026-10-13T10:00:00.000Z");
  });

  it("maps each slide to its desktop and mobile master", () => {
    for (const [index, expected] of EXPECTED.entries()) {
      const slide = HERO_CAMPAIGN_FIVE_SLIDES[index]!;
      expect(slide.desktopImage).toBe(`${HERO_CALIBRATED_ASSET_DIR}/${expected.desktop}`);
      expect(slide.mobileImage).toBe(`${HERO_CALIBRATED_ASSET_DIR}/${expected.mobile}`);
      expect(slide.desktopFocal).not.toBe(slide.mobileFocal);
      expect(slide.desktopFocal.startsWith("left")).toBe(true);
      expect(slide.primaryCta.href).toBe(expected.href);
      if ("secondaryHref" in expected) {
        expect(slide.secondaryCta?.href).toBe(expected.secondaryHref);
      } else {
        expect(slide.secondaryCta).toBeUndefined();
      }
    }
  });

  it("stores 3840×2160 desktop and 2880×2160 mobile masters", () => {
    for (const expected of EXPECTED) {
      const desktop = webpSize(
        path.join(publicRoot, HERO_CALIBRATED_ASSET_DIR.slice(1), expected.desktop),
      );
      const mobile = webpSize(
        path.join(publicRoot, HERO_CALIBRATED_ASSET_DIR.slice(1), expected.mobile),
      );
      expect(desktop).toEqual({ width: 3840, height: 2160 });
      expect(mobile).toEqual({ width: 2880, height: 2160 });
    }
  });

  it("keeps the previous reborn-5 generation on disk", () => {
    for (const name of [
      "H01-special-offers-native-lossless.webp",
      "H01-special-offers-1280.webp",
      "H05-industrial-machines-native-lossless.webp",
      "H05-industrial-machines-1280.webp",
    ]) {
      expect(existsSync(path.join(publicRoot, "images/hero/reborn-5", name))).toBe(true);
    }
  });

  it("keeps compact art direction on the same breakpoint as the compact layout", () => {
    expect(CAMPAIGN_MOBILE_SOURCE_MAX_PX).toBe(CAMPAIGN_COMPACT_MAX_PX);
    expect(CAMPAIGN_COMPACT_MAX_PX).toBe(1023);
    for (const slide of HERO_CAMPAIGN_FIVE_SLIDES) {
      expect(campaignMediaForSlide(slide.id).compactAspect).toBe(DEFAULT_COMPACT_ASPECT);
    }
  });
});
