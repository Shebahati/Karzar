import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parseDesignedHeroPack } from "@/features/home/hero-design";
import type { DesignedHeroPack } from "@/types/hero-design";

const publishedPath = path.join(process.cwd(), "public", "hero-design.json");

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
            imageUrl: "/images/hero/v2/desktop/hero-special-offers.png",
            mobileImageUrl: "/images/hero/v2/mobile/hero-special-offers-mobile.png",
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
    expect(pack!.slides.some((s) => s.id === "slide_special_offers")).toBe(true);
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
