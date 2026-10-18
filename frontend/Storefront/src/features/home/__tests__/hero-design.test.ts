import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  HERO_CAMPAIGN_FIVE_SLIDES,
  HERO_CAMPAIGN_FEATURED_KEYS,
  buildFiveHeroPublishedPack,
} from "@/config/hero-campaign-five";
import { parseDesignedHeroPack } from "@/features/home/hero-design";
import type { DesignedHeroPack } from "@/types/hero-design";

const publishedPath = path.join(process.cwd(), "public", "hero-design.json");

const EXPECTED_ORDER = [
  "discounts",
  "metrology",
  "inserts",
  "endmills",
  "industrial-machines",
] as const;

function minimalPack(overrides: Partial<DesignedHeroPack> = {}): DesignedHeroPack {
  return {
    version: 1,
    publishedAt: null,
    slides: [
      {
        id: "slide_test",
        name: "Test",
        sortOrder: 0,
        isActive: true,
        config: {
          version: 1,
          minHeight: 600,
          animation: "none",
          background: {
            mode: "image",
            imageUrl:
              "/images/hero/reborn-5/calibrated-20261018/H01-special-offers-desktop-16x9.webp",
            mobileImageUrl:
              "/images/hero/reborn-5/calibrated-20261018/H01-special-offers-mobile-4x3.webp",
            color: "#000",
            focal: "center",
          },
          overlay: {
            mode: "solid",
            solidColor: "#000",
            gradientFrom: "#000",
            gradientTo: "#000",
            gradientAngle: 0,
            opacity: 1,
          },
          typography: {
            title: "SSR Hero Title",
            subtitle: "Subtitle",
            titleColor: "#fff",
            subtitleColor: "#fff",
            titleSize: 32,
            subtitleSize: 16,
            align: "start",
            position: { x: 5, y: 20 },
            maxWidth: 480,
          },
          buttons: [],
          badges: [],
          carousel: {
            enabled: false,
            categorySlug: "",
            categoryLabel: "",
            position: { x: 0, y: 0 },
            maxItems: 4,
          },
        },
      },
    ],
    ...overrides,
  };
}

describe("parseDesignedHeroPack", () => {
  it("parses valid version 1 pack", () => {
    const pack = parseDesignedHeroPack(minimalPack());
    expect(pack?.version).toBe(1);
    expect(pack?.slides.length).toBe(1);
  });

  it("parses published hero-design.json", () => {
    const raw = JSON.parse(readFileSync(publishedPath, "utf8")) as unknown;
    const pack = parseDesignedHeroPack(raw);
    expect(pack).not.toBeNull();
    expect(pack!.slides.some((s) => s.id === "slide_h01_special_offers")).toBe(true);
  });

  it("returns null when slides missing", () => {
    expect(parseDesignedHeroPack({ version: 1 })).toBeNull();
  });

  it("returns null when slides empty", () => {
    expect(parseDesignedHeroPack(minimalPack({ slides: [] }))).toBeNull();
  });

  it("returns null for wrong version", () => {
    expect(parseDesignedHeroPack({ version: 2, slides: [{}] })).toBeNull();
  });

  it("returns null for non-object input", () => {
    expect(parseDesignedHeroPack(null)).toBeNull();
    expect(parseDesignedHeroPack("bad")).toBeNull();
  });
});

describe("five-hero reborn campaign contract", () => {
  it("campaign module defines five ordered keys", () => {
    expect(HERO_CAMPAIGN_FIVE_SLIDES).toHaveLength(5);
    expect(HERO_CAMPAIGN_FEATURED_KEYS).toEqual([...EXPECTED_ORDER]);
  });

  it("published pack matches five-slide dock mapping", () => {
    const pack = buildFiveHeroPublishedPack();
    const active = pack.slides.filter((s) => s.isActive);
    expect(active).toHaveLength(5);
    expect(active.map((s) => s.config.linkedOrbKey)).toEqual([...EXPECTED_ORDER]);

    const featured = pack.categoryDock!.categories
      .filter((c) => c.featuredOrder != null)
      .sort((a, b) => (a.featuredOrder ?? 0) - (b.featuredOrder ?? 0));
    expect(featured.map((c) => c.key)).toEqual([...EXPECTED_ORDER]);
    expect(featured.map((c) => c.featuredOrder)).toEqual([0, 1, 2, 3, 4]);
  });

  it("on-disk hero-design.json matches campaign contract", () => {
    const raw = JSON.parse(readFileSync(publishedPath, "utf8")) as unknown;
    const pack = parseDesignedHeroPack(raw)!;
    const keys = pack.slides
      .filter((s) => s.isActive)
      .sort((a, b) => a.sortOrder - b.sortOrder)
      .map((s) => s.config.linkedOrbKey);
    expect(keys).toEqual([...EXPECTED_ORDER]);
    expect(pack.slides.some((s) => s.config.linkedOrbKey === "workholding")).toBe(false);
    expect(pack.slides.some((s) => s.config.linkedOrbKey === "insert-tools")).toBe(false);
  });

  it("uses exact Persian H01 title and H03 dual CTAs", () => {
    const pack = buildFiveHeroPublishedPack();
    const h01 = pack.slides.find((s) => s.config.linkedOrbKey === "discounts")!;
    expect(h01.config.typography.title).toBe("تخفیف‌های ویژه‌ی کارزار");
    expect(h01.config.buttons[0]?.action.value).toBe("/catalog?on_sale=1");

    const h03 = pack.slides.find((s) => s.config.linkedOrbKey === "inserts")!;
    expect(h03.config.typography.title).toBe("اینسرت و ابزارهای اینسرتی");
    expect(h03.config.buttons.map((b) => b.label)).toEqual([
      "مشاهده اینسرت‌ها",
      "مشاهده ابزارهای اینسرتی",
    ]);
    expect(h03.config.buttons.map((b) => b.action.value)).toEqual([
      "/categories/insert",
      "/categories/abzar-inserti",
    ]);
  });

  it("uses calibrated reborn-5 webp assets per slide", () => {
    const pack = buildFiveHeroPublishedPack();
    const onDisk = parseDesignedHeroPack(JSON.parse(readFileSync(publishedPath, "utf8")))!;
    expect(pack.slides).toHaveLength(5);
    expect(onDisk.slides.map((s) => s.id)).toEqual(pack.slides.map((s) => s.id));
    for (const slide of pack.slides) {
      const published = onDisk.slides.find((s) => s.id === slide.id)!;
      expect(slide.config.background.imageUrl).toMatch(
        /\/calibrated-20261018\/H0\d-.*-desktop-16x9\.webp$/,
      );
      expect(slide.config.background.mobileImageUrl).toMatch(
        /\/calibrated-20261018\/H0\d-.*-mobile-4x3\.webp$/,
      );
      expect(published.config.background.imageUrl).toBe(slide.config.background.imageUrl);
      expect(published.config.background.mobileImageUrl).toBe(
        slide.config.background.mobileImageUrl,
      );
      expect(published.config.background.focal).toBe(slide.config.background.focal);
    }
  });
});
