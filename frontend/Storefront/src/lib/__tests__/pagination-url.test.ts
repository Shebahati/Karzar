import { describe, expect, it } from "vitest";
import {
  applyCatalogParamPatch,
  buildPaginatedHref,
  isPageBeyondTotal,
  parsePageParam,
} from "@/lib/pagination-url";

describe("parsePageParam", () => {
  it("defaults missing/invalid to page 1", () => {
    expect(parsePageParam(undefined)).toBe(1);
    expect(parsePageParam("")).toBe(1);
    expect(parsePageParam("abc")).toBe(1);
    expect(parsePageParam("0")).toBe(1);
    expect(parsePageParam("-1")).toBe(1);
    expect(parsePageParam("1.5")).toBe(1);
  });

  it("parses positive integers", () => {
    expect(parsePageParam("1")).toBe(1);
    expect(parsePageParam("2")).toBe(2);
    expect(parsePageParam("12")).toBe(12);
  });
});

describe("buildPaginatedHref", () => {
  it("omits page on page 1", () => {
    const sp = new URLSearchParams("brand=5&page=1");
    expect(buildPaginatedHref("/catalog", sp, 1)).toBe("/catalog?brand=5");
  });

  it("preserves facets when changing page", () => {
    const sp = new URLSearchParams("brand=5&country=ژاپن");
    const href = buildPaginatedHref("/catalog", sp, 2);
    const q = new URL(href, "https://example.com").searchParams;
    expect(q.get("brand")).toBe("5");
    expect(q.get("country")).toBe("ژاپن");
    expect(q.get("page")).toBe("2");
  });
});

describe("applyCatalogParamPatch", () => {
  it("clears page when filters change", () => {
    const base = new URLSearchParams("brand=5&page=5");
    const next = applyCatalogParamPatch(base, { sort: "price_asc" });
    expect(next.get("page")).toBeNull();
    expect(next.get("sort")).toBe("price_asc");
    expect(next.get("brand")).toBe("5");
  });

  it("clears page on brand change", () => {
    const base = new URLSearchParams("page=5&brand=1");
    const next = applyCatalogParamPatch(base, { brand: "2" });
    expect(next.get("page")).toBeNull();
    expect(next.get("brand")).toBe("2");
  });

  it("clears page on search change", () => {
    const base = new URLSearchParams("page=5&search=old");
    const next = applyCatalogParamPatch(base, { search: "new" });
    expect(next.get("page")).toBeNull();
    expect(next.get("search")).toBe("new");
  });

  it("clears page on price change", () => {
    const base = new URLSearchParams("page=5");
    const next = applyCatalogParamPatch(base, { min_price: 1000 });
    expect(next.get("page")).toBeNull();
    expect(next.get("min_price")).toBe("1000");
  });
});

describe("isPageBeyondTotal", () => {
  it("flags out-of-range pages", () => {
    expect(isPageBeyondTotal(999, 40, 20)).toBe(true);
    expect(isPageBeyondTotal(2, 40, 20)).toBe(false);
    expect(isPageBeyondTotal(1, 40, 20)).toBe(false);
  });
});
