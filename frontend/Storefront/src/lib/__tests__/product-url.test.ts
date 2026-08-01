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

  it("decode-once then encode-once for API path segments", () => {
    expect(safeDecodeURIComponent("%D8%A7%D8%A8%D8%B2%D8%A7%D8%B1")).toBe("ابزار");
    expect(safeDecodeURIComponent("ابزار")).toBe("ابزار");
    const encoded = encodeSlugPathSegment("%D8%A7%D8%A8%D8%B2%D8%A7%D8%B1");
    expect(decodeURIComponent(encoded)).toBe("ابزار");
    expect(encodeSlugPathSegment(encoded)).toBe(encoded);
  });
});
