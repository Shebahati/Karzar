import { describe, expect, it } from "vitest";
import { resolveProductL1Category } from "@/components/product/pdp-category-orbit";
import type { CategoryFlat } from "@/types/category";

function cat(
  partial: Partial<CategoryFlat> & Pick<CategoryFlat, "id" | "name">,
): CategoryFlat {
  return {
    parent_id: null,
    depth: 1,
    is_leaf: false,
    is_selectable: false,
    breadcrumb: [partial.name],
    ancestor_ids: [],
    ...partial,
  };
}

describe("resolveProductL1Category", () => {
  const roots = [
    cat({ id: 10, name: "اندازه‌گیری", slug: "andaze-giri", parent_id: null, depth: 1 }),
    cat({
      id: 20,
      name: "کولیس",
      slug: "colis",
      parent_id: 10,
      depth: 2,
      ancestor_ids: [10],
      breadcrumb: ["اندازه‌گیری", "کولیس"],
      is_leaf: true,
      is_selectable: true,
    }),
    cat({
      id: 30,
      name: "دیجیتال",
      slug: "digital",
      parent_id: 20,
      depth: 3,
      ancestor_ids: [10, 20],
      breadcrumb: ["اندازه‌گیری", "کولیس", "دیجیتال"],
      is_leaf: true,
      is_selectable: true,
    }),
  ];

  it("returns root from ancestor_ids[0]", () => {
    const l1 = resolveProductL1Category(
      { id: 30, ancestor_ids: [10, 20] },
      roots,
    );
    expect(l1?.id).toBe(10);
    expect(l1?.name).toBe("اندازه‌گیری");
  });

  it("returns leaf itself when it is L1", () => {
    const l1 = resolveProductL1Category({ id: 10, ancestor_ids: [] }, roots);
    expect(l1?.id).toBe(10);
  });

  it("returns null when category missing", () => {
    expect(resolveProductL1Category(null, roots)).toBeNull();
    expect(resolveProductL1Category({ id: 999 }, roots)).toBeNull();
  });
});
