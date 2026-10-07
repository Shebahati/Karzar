import { describe, expect, it } from "vitest";
import {
  encodedProductSlugPath,
  numericProductRedirectPath,
  productPath,
} from "@/lib/product-url";

describe("SEO Wave 2B-1 numeric vs slug PDP contract", () => {
  const product = { id: 42, slug: "some-distinct-slug" };

  it("numeric param with distinct slug must redirect to slug path", () => {
    expect(numericProductRedirectPath("42", product)).toBe(
      productPath(product),
    );
    expect(numericProductRedirectPath("42", product)).toBe("/product/some-distinct-slug");
  });

  it("slug PDP path is self-canonical via productPath", () => {
    expect(productPath(product)).toBe("/product/some-distinct-slug");
  });

  it("does not redirect when slug equals numeric key", () => {
    const numericSlug = { id: 99, slug: "99" };
    expect(numericProductRedirectPath("99", numericSlug)).toBeNull();
  });

  it("encodes Unicode slug exactly once for Location", () => {
    const path = encodedProductSlugPath("مدل-تست");
    expect(path).toBe(`/product/${encodeURIComponent("مدل-تست")}`);
    expect(path).not.toContain("%25");
  });
});
