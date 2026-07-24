import { describe, expect, it } from "vitest";
import {
  buildNavGroups,
  categoryHref,
  filterNonEmptyTree,
  NAV_GROUPS,
} from "@/config/nav-groups";

describe("nav-groups", () => {
  const roots = [
    { id: 7, name: "اندازه گیری", slug: "andaze-giri-7", product_count: 10, subcategories: [] },
    { id: 3, name: "اینسرت", slug: "insert-3", product_count: 5, subcategories: [] },
    { id: 5, name: "مته", slug: "mete-5", product_count: 2, subcategories: [] },
    { id: 1, name: "ابزارگیر", slug: "abzargir-1", product_count: 3, subcategories: [] },
    { id: 9, name: "دستگاه‌های صنعتی", slug: "machines-9", product_count: 1, subcategories: [] },
    { id: 99, name: "Insert", slug: "insert-dead", product_count: 0, subcategories: [] },
  ];

  it("puts metrology first and hides empty roots", () => {
    const groups = buildNavGroups(roots);
    expect(groups[0]?.id).toBe("metrology");
    expect(groups[0]?.highlight).toBe(true);
    expect(groups.some((g) => g.roots.some((r) => r.id === 99))).toBe(false);
    const cutting = groups.find((g) => g.id === "cutting");
    expect(cutting?.roots.map((r) => r.id).sort()).toEqual([3, 5]);
  });

  it("filters empty subtrees", () => {
    const tree = filterNonEmptyTree([
      {
        id: 1,
        name: "root",
        product_count: 0,
        subcategories: [
          { id: 2, name: "empty", product_count: 0, subcategories: [] },
          { id: 3, name: "full", product_count: 2, subcategories: [] },
        ],
      },
    ]);
    expect(tree).toHaveLength(1);
    expect(tree[0].subcategories?.map((c) => c.id)).toEqual([3]);
  });

  it("prefers hub href when slug present", () => {
    expect(categoryHref({ id: 7, slug: "andaze-giri-7" })).toBe("/categories/andaze-giri-7");
    expect(categoryHref({ id: 7 })).toBe("/catalog?category=7");
  });

  it("defines five merchandising groups", () => {
    expect(NAV_GROUPS).toHaveLength(5);
    expect(NAV_GROUPS[0].id).toBe("metrology");
  });
});
