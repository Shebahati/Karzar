import type { CategoryFlat, CategoryTreeNode } from "@/types/category";

/** Flatten nested tree into rows with depth, breadcrumb, and leaf metadata. */
export function flattenCategoryTree(
  nodes: CategoryTreeNode[],
  ancestorIds: number[] = [],
  ancestorNames: string[] = [],
  depth = 1,
): CategoryFlat[] {
  const rows: CategoryFlat[] = [];
  for (const node of nodes) {
    const breadcrumb = [...ancestorNames, node.name];
    const isLeaf = node.subcategories.length === 0;
    rows.push({
      id: node.id,
      name: node.name,
      parent_id: node.parent_id,
      depth,
      is_leaf: isLeaf,
      is_selectable: isLayer3Leaf(depth, isLeaf),
      breadcrumb,
      ancestor_ids: ancestorIds,
    });
    rows.push(
      ...flattenCategoryTree(
        node.subcategories,
        [...ancestorIds, node.id],
        breadcrumb,
        depth + 1,
      ),
    );
  }
  return rows;
}

/** Layer 3 = exactly two ancestors (parent + grandparent), leaf = no children. */
export function isLayer3Leaf(depth: number, isLeaf: boolean): boolean {
  return depth === 3 && isLeaf;
}

/**
 * Enrich a flat parent_id list with depth metadata when the API omits it.
 * Useful when only id/name/parent_id are available.
 */
export function enrichFlatCategories(categories: CategoryFlat[]): CategoryFlat[] {
  const byId = new Map(categories.map((c) => [c.id, c]));
  const childCount = new Map<number, number>();

  for (const category of categories) {
    if (category.parent_id != null) {
      childCount.set(category.parent_id, (childCount.get(category.parent_id) ?? 0) + 1);
    }
  }

  return categories.map((category) => {
    const chain: CategoryFlat[] = [];
    const visited = new Set<number>();
    let current: CategoryFlat | undefined = category;

    while (current) {
      if (visited.has(current.id)) break;
      visited.add(current.id);
      chain.push(current);
      current =
        current.parent_id != null ? byId.get(current.parent_id) : undefined;
    }

    const depth = category.depth ?? chain.length;
    const isLeaf = category.is_leaf ?? (childCount.get(category.id) ?? 0) === 0;
    const breadcrumb =
      category.breadcrumb?.length > 0
        ? category.breadcrumb
        : [...chain].reverse().map((node) => node.name);
    const ancestorIds =
      category.ancestor_ids?.length > 0
        ? category.ancestor_ids
        : chain
            .slice(1)
            .map((node) => node.id)
            .reverse();

    return {
      ...category,
      depth,
      is_leaf: isLeaf,
      breadcrumb,
      ancestor_ids: ancestorIds,
      is_selectable: isLayer3Leaf(depth, isLeaf),
    };
  });
}
