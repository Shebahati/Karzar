import { describe, expect, it } from "vitest";
import {
  MAX_CATEGORY_DEPTH,
  MIN_PRODUCT_CATEGORY_DEPTH,
  enrichFlatCategories,
  isSelectableProductCategory,
} from "@/features/catalog/utils/category-tree";
import { getSelectableCategories } from "@/features/catalog/utils/specifications";
import type { CategoryFlat } from "@/types/category";

/** Minimal rows without depth/leaf so enrich recomputes from parent_id. */
function raw(
  id: number,
  name: string,
  parent_id: number | null,
): CategoryFlat {
  return {
    id,
    name,
    parent_id,
    depth: undefined as unknown as number,
    is_leaf: undefined as unknown as boolean,
    is_selectable: false,
    breadcrumb: [],
    ancestor_ids: [],
  };
}

describe("TD-001 selectable depth 2|3", () => {
  it("mirrors backend min/max product depth constants", () => {
    expect(MIN_PRODUCT_CATEGORY_DEPTH).toBe(2);
    expect(MAX_CATEGORY_DEPTH).toBe(3);
  });

  it("allows leaf depth 2 and 3, rejects L1 and non-leaves", () => {
    expect(isSelectableProductCategory(1, true)).toBe(false);
    expect(isSelectableProductCategory(2, true)).toBe(true);
    expect(isSelectableProductCategory(3, true)).toBe(true);
    expect(isSelectableProductCategory(2, false)).toBe(false);
    expect(isSelectableProductCategory(3, false)).toBe(false);
    expect(isSelectableProductCategory(4, true)).toBe(false);
  });

  it("getSelectableCategories includes depth-2 leaves after enrich", () => {
    const rows = [
      raw(1, "L1", null),
      raw(2, "L2-leaf", 1),
      raw(3, "L2-hub", 1),
      raw(4, "L3-leaf", 3),
    ];
    for (const r of rows) {
      delete (r as { depth?: number }).depth;
      delete (r as { is_leaf?: boolean }).is_leaf;
    }
    const selectable = getSelectableCategories(rows);
    expect(selectable.map((c) => c.id).sort()).toEqual([2, 4]);
    expect(selectable.every((c) => c.is_selectable)).toBe(true);
  });

  it("enrichFlatCategories sets is_selectable for depth-2 leaves", () => {
    const rows = [raw(1, "L1", null), raw(2, "L2-leaf", 1)];
    for (const r of rows) {
      delete (r as { depth?: number }).depth;
      delete (r as { is_leaf?: boolean }).is_leaf;
    }
    const enriched = enrichFlatCategories(rows);
    const leaf = enriched.find((c) => c.id === 2)!;
    expect(leaf.depth).toBe(2);
    expect(leaf.is_leaf).toBe(true);
    expect(leaf.is_selectable).toBe(true);
  });
});
