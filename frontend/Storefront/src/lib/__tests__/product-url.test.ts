import { describe, expect, it } from "vitest";
import {
  encodeSlugPathSegment,
  isNumericProductParam,
  productPath,
  safeDecodeURIComponent,
} from "@/lib/product-url";

describe("product-url", () => {
  it("detects numeric id params", () => {
    expect(isNumericProductParam("42")).toBe(true);
    expect(isNumericProductParam(" 99 ")).toBe(true);
    expect(isNumericProductParam("ins-1108")).toBe(false);
    expect(isNumericProductParam("42a")).toBe(false);
  });

  it("prefers slug path when present", () => {
    expect(productPath({ id: 42, slug: "ins-1108" })).toBe("/product/ins-1108");
    expect(productPath({ id: 42, slug: "  " })).toBe("/product/42");
    expect(productPath({ id: 42, slug: null })).toBe("/product/42");
  });

  it("safeDecodeURIComponent decodes once and tolerates plain/malformed", () => {
    const persian = "میله-اینسایز";
    const encoded = encodeURIComponent(persian);
    expect(safeDecodeURIComponent(encoded)).toBe(persian);
    expect(safeDecodeURIComponent(persian)).toBe(persian);
    expect(safeDecodeURIComponent("%E0%A4%A")).toBe("%E0%A4%A");
  });

  it("encodeSlugPathSegment never double-encodes a pre-encoded slug", () => {
    const persian = "میله-اینسایز";
    const once = encodeURIComponent(persian);
    expect(encodeSlugPathSegment(persian)).toBe(once);
    expect(encodeSlugPathSegment(once)).toBe(once);
    expect(encodeSlugPathSegment(` ${once} `)).toBe(once);
  });
});
