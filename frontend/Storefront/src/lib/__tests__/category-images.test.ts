import { describe, expect, it } from "vitest";
import {
  CATEGORY_IMAGE_BY_ID,
  resolveCategoryImage,
} from "@/lib/category-images";

/** Live L1 root ids observed on api.karzartools.com (2026-07-27). */
const LIVE_L1_IDS = [
  1, 2, 4, 5, 6, 8, 9, 56, 81, 87, 154, 165, 186, 187, 188,
] as const;

describe("category images (CAT-003)", () => {
  it("covers every live L1 root with curated art", () => {
    for (const id of LIVE_L1_IDS) {
      expect(CATEGORY_IMAGE_BY_ID[id], `missing curated image for L1 id=${id}`).toBeTruthy();
    }
  });

  it("resolves helicoil roots by id and Persian name", () => {
    expect(resolveCategoryImage({ id: 186, name: "فنر هلی کویل" })).toBe(
      "/images/categories/helicoil-spring.jpg",
    );
    expect(resolveCategoryImage({ id: 187, name: "قلاویز هلی کویل" })).toBe(
      "/images/categories/helicoil-tap.jpg",
    );
    expect(resolveCategoryImage({ id: 188, name: "کیت کامل هلی کویل" })).toBe(
      "/images/categories/helicoil-kit.jpg",
    );
  });

  it("falls back to API image_url when not curated", () => {
    expect(
      resolveCategoryImage({
        id: 9999,
        name: "ناشناخته",
        image_url: "https://api.example/static/x.jpg",
      }),
    ).toBe("https://api.example/static/x.jpg");
  });
});
