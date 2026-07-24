import { describe, expect, it } from "vitest";
import {
  buildNavGroups,
  categoryHref,
  filterNonEmptyTree,
  isMetrologyRoot,
  isTaxonomyRoot,
  NAV_GROUPS,
  orderedVisibleRoots,
  sortByNavOrder,
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

  it("flattens groups into ordered visible roots", () => {
    const ordered = orderedVisibleRoots(roots);
    expect(ordered.map((r) => r.id)).toEqual([7, 3, 5, 1, 9]);
    expect(ordered[0]?.name).toBe("اندازه گیری");
    expect(isMetrologyRoot(ordered[0]!)).toBe(true);
    expect(isMetrologyRoot(ordered[1]!)).toBe(false);
  });

  it("detects taxonomy roots via parent_id null / depth 1 (not depth 0)", () => {
    expect(isTaxonomyRoot({ parent_id: null, depth: 1 })).toBe(true);
    expect(isTaxonomyRoot({ parent_id: null, depth: 0 })).toBe(true);
    expect(isTaxonomyRoot({ parent_id: 7, depth: 2 })).toBe(false);
    expect(isTaxonomyRoot({ depth: 1 })).toBe(true);
    expect(isTaxonomyRoot({ depth: 0 })).toBe(false);
    expect(isTaxonomyRoot({ depth: 2 })).toBe(false);
  });

  it("sortByNavOrder matches orderedVisibleRoots for flat L1", () => {
    const flat = [
      { id: 5, name: "مته", product_count: 2, parent_id: null as number | null, depth: 1 },
      { id: 7, name: "اندازه گیری", product_count: 10, parent_id: null as number | null, depth: 1 },
      { id: 3, name: "اینسرت", product_count: 5, parent_id: null as number | null, depth: 1 },
    ];
    expect(sortByNavOrder(flat).map((r) => r.id)).toEqual([7, 3, 5]);
  });
});
