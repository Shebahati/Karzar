import type { Category, CategoryFlat, CategoryTreeNode } from "@/types/category";
import { CATEGORY_ICONS } from "@/data/mock-data";

/** Build depth/leaf/breadcrumb metadata for a flat category list. */
export function enrichCategories(categories: Category[]): CategoryFlat[] {
  const byId = new Map(categories.map((c) => [c.id, c]));
  const childCount = new Map<number, number>();
  for (const c of categories) {
    if (c.parent_id != null) {
      childCount.set(c.parent_id, (childCount.get(c.parent_id) ?? 0) + 1);
    }
  }

  return categories.map((c) => {
    const ancestor_ids: number[] = [];
    const breadcrumb: string[] = [];
    let cursor: Category | undefined = c;
    while (cursor) {
      breadcrumb.unshift(cursor.name);
      const parentId: number | null = cursor.parent_id;
      if (parentId == null) break;
      ancestor_ids.unshift(parentId);
      cursor = byId.get(parentId);
    }
    const depth = breadcrumb.length;
    const is_leaf = (childCount.get(c.id) ?? 0) === 0;
    return {
      ...c,
      depth,
      is_leaf,
      is_selectable: depth === 3 && is_leaf,
      breadcrumb,
      ancestor_ids,
      icon: c.parent_id == null ? CATEGORY_ICONS[c.id] : undefined,
    };
  });
}

/** Assemble a nested tree from a flat category list. */
export function buildCategoryTree(categories: Category[]): CategoryTreeNode[] {
  const nodes = new Map<number, CategoryTreeNode>();
  for (const c of categories) {
    nodes.set(c.id, {
      ...c,
      icon: c.parent_id == null ? CATEGORY_ICONS[c.id] : undefined,
      subcategories: [],
    });
  }
  const roots: CategoryTreeNode[] = [];
  for (const c of categories) {
    const node = nodes.get(c.id)!;
    if (c.parent_id != null && nodes.has(c.parent_id)) {
      nodes.get(c.parent_id)!.subcategories.push(node);
    } else {
      roots.push(node);
    }
  }
  return roots;
}

/** Collect the ids of a category and all of its descendants. */
export function collectDescendantIds(
  categories: Category[],
  rootId: number,
): number[] {
  const childrenByParent = new Map<number, number[]>();
  for (const c of categories) {
    if (c.parent_id != null) {
      const arr = childrenByParent.get(c.parent_id) ?? [];
      arr.push(c.id);
      childrenByParent.set(c.parent_id, arr);
    }
  }
  const result: number[] = [];
  const stack = [rootId];
  while (stack.length) {
    const id = stack.pop()!;
    result.push(id);
    const kids = childrenByParent.get(id);
    if (kids) stack.push(...kids);
  }
  return result;
}
