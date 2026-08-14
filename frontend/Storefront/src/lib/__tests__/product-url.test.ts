import { describe, expect, it } from "vitest";
import {
  catalogProductByIdUrl,
  encodeSlugPathSegment,
  encodedProductSlugPath,
  isNumericProductParam,
  numericProductPathId,
  numericProductRedirectPath,
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
    // Pre-encoded Next param must not become double-encoded (%25D8...).
    expect(encoded).not.toContain("%25");
    expect(encodeSlugPathSegment("کولیس-دیجیتال")).toBe(
      encodeURIComponent("کولیس-دیجیتال"),
    );
    expect(
      encodeSlugPathSegment(encodeURIComponent("کولیس-دیجیتال")),
    ).toBe(encodeURIComponent("کولیس-دیجیتال"));
  });

  it("permanently maps numeric id params to slug path when slug exists", () => {
    expect(
      numericProductRedirectPath("7115", { id: 7115, slug: "digital-caliper" }),
    ).toBe("/product/digital-caliper");
    expect(
      numericProductRedirectPath("7115", {
        id: 7115,
        slug: "کولیس-دیجیتال",
      }),
    ).toBe("/product/کولیس-دیجیتال");
    expect(
      numericProductRedirectPath("digital-caliper", {
        id: 7115,
        slug: "digital-caliper",
      }),
    ).toBeNull();
    expect(
      numericProductRedirectPath("7115", { id: 7115, slug: null }),
    ).toBeNull();
    expect(
      numericProductRedirectPath("7115", { id: 7115, slug: "7115" }),
    ).toBeNull();
  });

  it("extracts numeric id only from a PDP path", () => {
    expect(numericProductPathId("/product/6587")).toBe("6587");
    expect(numericProductPathId("/product/6587/")).toBe("6587");
    expect(numericProductPathId("/product/مدل-ast-cor305p")).toBeNull();
    expect(numericProductPathId("/product/ins-1108")).toBeNull();
    expect(numericProductPathId("/catalog")).toBeNull();
    expect(numericProductPathId("/product/6587/extra")).toBeNull();
  });

  it("encodes slug Location paths exactly once", () => {
    expect(encodedProductSlugPath("digital-caliper")).toBe(
      "/product/digital-caliper",
    );
    expect(encodedProductSlugPath("مدل-ast-cor305p")).toBe(
      `/product/${encodeURIComponent("مدل-ast-cor305p")}`,
    );
    expect(encodedProductSlugPath(encodeURIComponent("مدل-ast-cor305p"))).toBe(
      `/product/${encodeURIComponent("مدل-ast-cor305p")}`,
    );
    expect(catalogProductByIdUrl("https://api.karzartools.com/api/v1/", "6587")).toBe(
      "https://api.karzartools.com/api/v1/products/6587",
    );
  });
});
