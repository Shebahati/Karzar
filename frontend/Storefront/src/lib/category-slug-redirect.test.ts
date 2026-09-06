import { describe, expect, it } from "vitest";

import {
  categoryHubPath,
  resolveCategorySlugRedirect,
} from "@/lib/category-slug-redirect";

describe("category slug redirects", () => {
  it("returns null when no redirect is configured", () => {
    expect(resolveCategorySlugRedirect("andaze-daghigh")).toBeNull();
  });

  it("builds encoded category hub paths", () => {
    expect(categoryHubPath("مته-hss")).toBe(
      `/categories/${encodeURIComponent("مته-hss")}`,
    );
  });
});
