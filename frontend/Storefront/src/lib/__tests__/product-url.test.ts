import { describe, expect, it } from "vitest";

import { productHref } from "@/lib/product-url";

describe("productHref", () => {
  it("prefers slug over numeric id", () => {
    expect(productHref({ id: 1, slug: "bsh-gsb-13re" })).toBe("/product/bsh-gsb-13re");
  });

  it("falls back to id when slug is missing", () => {
    expect(productHref({ id: 42 })).toBe("/product/42");
  });
});
