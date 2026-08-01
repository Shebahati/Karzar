import { describe, expect, it } from "vitest";

import {
  edgeStatusLabel,
  edgeTypeLabel,
  formatNodeRef,
  nodeTypeLabel,
} from "@/features/knowledge/edge-labels";

describe("knowledge edge labels", () => {
  it("labels the three KB-001 freeze edge types", () => {
    expect(edgeTypeLabel("PRODUCT_BELONGS_TO_CATEGORY")).toContain("دسته");
    expect(edgeTypeLabel("PRODUCT_BRANDED_AS")).toContain("برند");
    expect(edgeTypeLabel("ARTICLE_EXPLAINS_PRODUCT")).toContain("مقاله");
  });

  it("formats node refs for admin display", () => {
    expect(nodeTypeLabel("product")).toBe("محصول");
    expect(formatNodeRef("category", 56)).toBe("دسته #56");
    expect(edgeStatusLabel("asserted")).toBe("اعلام‌شده");
  });
});
