import { describe, expect, it } from "vitest";
import type { CategoryFlat } from "@/types/category";

function cat(
  partial: Pick<CategoryFlat, "id" | "name" | "slug" | "product_count">,
): CategoryFlat {
  return {
    parent_id: 0,
    depth: 2,
    is_leaf: true,
    is_selectable: true,
    breadcrumb: [partial.name],
    ancestor_ids: [],
    ...partial,
  };
}

/** Mirrors HubChildNav browseable filter — keep in sync with hub-child-nav.tsx */
function browsableChildren(childCategories: CategoryFlat[]) {
  return childCategories
    .filter((c) => Boolean(c.slug) && (c.product_count ?? 0) > 0)
    .sort((a, b) => (b.product_count ?? 0) - (a.product_count ?? 0));
}

function emptyStateCopy(opts: {
  hasActiveFilters: boolean;
  categoryName?: string;
}) {
  const title = opts.hasActiveFilters
    ? "با این فیلترها محصولی پیدا نشد"
    : opts.categoryName
      ? `فعلاً محصولی در «${opts.categoryName}» نیست`
      : "محصولی یافت نشد";
  return title;
}

describe("UX-001 PLP empty + hub IA helpers", () => {
  it("filters hub children to slug+stock and sorts by count", () => {
    const kids = [
      cat({ id: 1, name: "A", slug: "a", product_count: 2 }),
      cat({ id: 2, name: "B", slug: "b", product_count: 10 }),
      cat({ id: 3, name: "empty", slug: "e", product_count: 0 }),
      cat({ id: 4, name: "noslug", slug: "", product_count: 5 }),
    ];
    const out = browsableChildren(kids);
    expect(out.map((c) => c.id)).toEqual([2, 1]);
  });

  it("uses Persian empty titles for filter vs category vs generic", () => {
    expect(emptyStateCopy({ hasActiveFilters: true })).toContain("فیلتر");
    expect(emptyStateCopy({ hasActiveFilters: false, categoryName: "کولیس" })).toContain(
      "کولیس",
    );
    expect(emptyStateCopy({ hasActiveFilters: false })).toBe("محصولی یافت نشد");
  });
});
