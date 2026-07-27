import { describe, expect, it } from "vitest";
import {
  MAX_SITEMAP_URLS,
  capSitemapEntries,
  isEmptyCategoryHub,
  isFacetedSearchParams,
} from "@/lib/crawl-hygiene";

describe("isFacetedSearchParams", () => {
  it("treats clean catalog/hub as indexable", () => {
    expect(isFacetedSearchParams({})).toBe(false);
    expect(isFacetedSearchParams({ utm_source: "x" })).toBe(false);
  });

  it("flags brand/price/search/sort/spec traps", () => {
    expect(isFacetedSearchParams({ brand: "1,2" })).toBe(true);
    expect(isFacetedSearchParams({ min_price: "1000" })).toBe(true);
    expect(isFacetedSearchParams({ search: "کولیس" })).toBe(true);
    expect(isFacetedSearchParams({ sort: "price_asc" })).toBe(true);
    expect(isFacetedSearchParams({ spec_grade: "A" })).toBe(true);
    expect(isFacetedSearchParams({ roots: "12,13" })).toBe(true);
  });

  it("ignores empty facet values", () => {
    expect(isFacetedSearchParams({ brand: "", search: undefined })).toBe(false);
  });

  it("ignores mirrored category_* on hubs when asked", () => {
    expect(isFacetedSearchParams({ category: "12" })).toBe(true);
    expect(
      isFacetedSearchParams({ category: "12" }, { ignoreCategoryKeys: true }),
    ).toBe(false);
    expect(
      isFacetedSearchParams(
        { category: "12", brand: "3" },
        { ignoreCategoryKeys: true },
      ),
    ).toBe(true);
  });
});

describe("isEmptyCategoryHub", () => {
  it("soft-404 only when count is known zero", () => {
    expect(isEmptyCategoryHub(0)).toBe(true);
    expect(isEmptyCategoryHub(-1)).toBe(true);
    expect(isEmptyCategoryHub(1)).toBe(false);
    expect(isEmptyCategoryHub(undefined)).toBe(false);
    expect(isEmptyCategoryHub(null)).toBe(false);
  });
});

describe("capSitemapEntries", () => {
  it("keeps under Google 50k limit", () => {
    expect(MAX_SITEMAP_URLS).toBeLessThan(50_000);
    const entries = Array.from({ length: MAX_SITEMAP_URLS + 10 }, (_, i) => i);
    expect(capSitemapEntries(entries)).toHaveLength(MAX_SITEMAP_URLS);
  });
});
