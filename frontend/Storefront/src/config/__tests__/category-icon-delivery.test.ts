import fs from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { CURATED_CATEGORY_ICON_WEBP_BASENAMES } from "@/config/category-icon-allowlist";
import {
  categoryIconWebpExperimentEnabled,
  resolveCategoryIconSources,
} from "@/config/category-icon-delivery";

const storefrontRoot = path.resolve(__dirname, "../../..");

describe("category-icon-delivery", () => {
  const prev = process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP;

  afterEach(() => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = prev;
  });

  it("returns null when experiment flag off (baseline path)", () => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = "0";
    expect(categoryIconWebpExperimentEnabled()).toBe(false);
    expect(resolveCategoryIconSources("/category-icons/insert.png")).toBeNull();
    expect(resolveCategoryIconSources("/category-icons/takhfif.png")).toBeNull();
  });

  it("maps allowlisted curated png to webp when flag on", () => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = "1";
    expect(resolveCategoryIconSources("/category-icons/insert.png")).toEqual({
      png: "/category-icons/insert.png",
      webp: "/category-icons/webp/insert.webp",
    });
    expect(resolveCategoryIconSources("/category-icons/takhfif.png")).toEqual({
      png: "/category-icons/takhfif.png",
      webp: "/category-icons/webp/takhfif.webp",
    });
  });

  it("does not map unknown png under category-icons", () => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = "1";
    expect(resolveCategoryIconSources("/category-icons/custom-future.png")).toBeNull();
    expect(resolveCategoryIconSources("/category-icons/../evil.png")).toBeNull();
  });

  it("does not map external or non-png urls", () => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = "1";
    expect(resolveCategoryIconSources("https://cdn.example.com/icon.png")).toBeNull();
    expect(resolveCategoryIconSources("/category-icons/insert.webp")).toBeNull();
    expect(resolveCategoryIconSources("/other-icons/insert.png")).toBeNull();
  });

  it("every allowlisted basename has png and webp on disk", () => {
    for (const base of CURATED_CATEGORY_ICON_WEBP_BASENAMES) {
      const png = path.join(storefrontRoot, "public/category-icons", `${base}.png`);
      const webp = path.join(storefrontRoot, "public/category-icons/webp", `${base}.webp`);
      expect(fs.existsSync(png), `missing png ${base}`).toBe(true);
      expect(fs.existsSync(webp), `missing webp ${base}`).toBe(true);
    }
  });
});
