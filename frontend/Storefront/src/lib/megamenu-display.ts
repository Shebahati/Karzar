/**
 * Megamenu presentation helpers over the category tree.
 *
 * - Hides `megamenu_hidden` nodes
 * - Collapses padding «عمومی» singleton children into the parent leaf
 *   (safety net if DB still has filler leaves; prefer
 *   `scripts/remove_omumi_padding_leaves.py` for real cleanup)
 * - Honors `megamenu_as_leaf` (force terminal link, hide children)
 * - `megamenu_bold`: null = auto (branch headers bold; leaves normal)
 */

export interface MegamenuCategoryNode {
  id: number;
  name: string;
  slug?: string;
  parent_id?: number | null;
  product_count?: number;
  megamenu_hidden?: boolean;
  megamenu_as_leaf?: boolean;
  megamenu_bold?: boolean | null;
  subcategories?: MegamenuCategoryNode[];
}

/** Padding filler leaves like «عمومی» or «کولیس — عمومی» (no Unicode regex — SWC-safe). */
export function isPaddingLeafName(name: string): boolean {
  const n = (name || "").trim().replace(/\u200c/g, "");
  if (!n) return false;
  if (n === "عمومی") return true;
  // Ends with dash/separator + عمومی
  const separators = ["—", "-", "–", "ـ"];
  for (const sep of separators) {
    const idx = n.lastIndexOf(sep);
    if (idx >= 0 && n.slice(idx + sep.length).trim() === "عمومی") return true;
  }
  return false;
}

function hasProducts(node: MegamenuCategoryNode): boolean {
  return (node.product_count ?? 0) > 0;
}

/** Auto bold: branch with visible children → bold; terminal link → normal. */
export function resolveMegamenuBold(
  node: MegamenuCategoryNode,
  options: { isBranch: boolean },
): boolean {
  if (typeof node.megamenu_bold === "boolean") return node.megamenu_bold;
  return options.isBranch;
}

/**
 * Prepare a category subtree for megamenu rendering.
 * Returns null when the node (and descendants) should not appear.
 */
export function prepareMegamenuNode<T extends MegamenuCategoryNode>(
  node: T,
): (T & { subcategories: T[] }) | null {
  if (node.megamenu_hidden) return null;

  const rawKids = (node.subcategories ?? []) as T[];
  let kids = rawKids
    .map((child) => prepareMegamenuNode(child))
    .filter((child): child is T & { subcategories: T[] } => Boolean(child));

  // Collapse sole padding «عمومی» child into the parent (display parent as leaf).
  if (
    !node.megamenu_as_leaf &&
    kids.length === 1 &&
    isPaddingLeafName(kids[0].name) &&
    (kids[0].subcategories?.length ?? 0) === 0
  ) {
    kids = [];
  }

  if (node.megamenu_as_leaf) {
    kids = [];
  }

  const prepared = { ...node, subcategories: kids };
  if (!hasProducts(prepared) && kids.length === 0) return null;
  return prepared;
}

export function prepareMegamenuRoots<T extends MegamenuCategoryNode>(
  roots: T[],
): Array<T & { subcategories: T[] }> {
  return roots
    .map((root) => prepareMegamenuNode(root))
    .filter((root): root is T & { subcategories: T[] } => Boolean(root));
}
