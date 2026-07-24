/**
 * Merchandising display groups over taxonomy roots (FE-only; taxonomy stays ~10 roots).
 *
 * Locked IA (docs/constitution + category plan):
 * - Commerce SoR = product-type tree, depth ≤ 3, products on L3 leaves
 * - Brand / country = facets (not categories)
 * - Top nav megamenu = these 5 merchandising groups
 * - Browse surfaces (home, catalog carousel, mobile sheet) = ordered L1 type roots
 * - PLP filter = same product tree (drill-down), not a third taxonomy
 *
 * Order is intentional: Metrology first.
 */

export interface NavGroupDef {
  id: string;
  label: string;
  /** Highlight Metrology in menus. */
  highlight?: boolean;
  /** Match roots by exact name (Persian) or slug substring. */
  rootMatchers: string[];
}

export const NAV_GROUPS: NavGroupDef[] = [
  {
    id: "metrology",
    label: "اندازه‌گیری",
    highlight: true,
    rootMatchers: ["اندازه گیری", "اندازه‌گیری", "andaze", "measurement"],
  },
  {
    id: "cutting",
    label: "براده‌برداری",
    rootMatchers: [
      "اینسرت",
      "ابزار اینسرتی",
      "ابزار انگشتی",
      "انگشتی",
      "مته",
      "قلاویز",
      "insert",
    ],
  },
  {
    id: "holding",
    label: "ابزارگیری و گیرش",
    rootMatchers: ["ابزارگیر", "ابزار گیرشی"],
  },
  {
    id: "machines",
    label: "ماشین‌ها و تجهیزات",
    rootMatchers: ["دستگاه‌های صنعتی", "دستگاه های صنعتی"],
  },
  {
    id: "accessories",
    label: "لوازم جانبی",
    rootMatchers: ["لوازم جانبی صنعتی", "لوازم جانبی"],
  },
];

export interface CategoryLike {
  id: number;
  name: string;
  slug?: string;
  product_count?: number;
  subcategories?: CategoryLike[];
}

function normalize(s: string): string {
  return s.trim().replace(/\u200c/g, "").replace(/ي/g, "ی").replace(/ك/g, "ک").toLowerCase();
}

function matchesRoot(root: CategoryLike, matcher: string): boolean {
  const m = normalize(matcher);
  const name = normalize(root.name);
  const slug = normalize(root.slug ?? "");
  return name === m || name.includes(m) || slug.includes(m) || slug === m;
}

/** Prefer hub URL when slug exists; dual-run keeps /catalog?category=id working. */
export function categoryHref(category: { id: number; slug?: string | null }): string {
  if (category.slug) return `/categories/${category.slug}`;
  return `/catalog?category=${category.id}`;
}

export function hasProducts(node: CategoryLike): boolean {
  return (node.product_count ?? 0) > 0;
}

/** Hide empty nodes; prune empty children recursively. */
export function filterNonEmptyTree<T extends CategoryLike>(nodes: T[]): T[] {
  return nodes
    .map((node) => {
      const kids = filterNonEmptyTree((node.subcategories ?? []) as T[]);
      return { ...node, subcategories: kids };
    })
    .filter((node) => hasProducts(node) || (node.subcategories?.length ?? 0) > 0) as T[];
}

export interface ResolvedNavGroup<T extends CategoryLike> {
  id: string;
  label: string;
  highlight: boolean;
  roots: T[];
  product_count: number;
}

export function buildNavGroups<T extends CategoryLike>(
  roots: T[],
  groups: NavGroupDef[] = NAV_GROUPS,
): ResolvedNavGroup<T>[] {
  const visible = filterNonEmptyTree(roots);
  const assigned = new Set<number>();
  const resolved: ResolvedNavGroup<T>[] = [];

  for (const group of groups) {
    const matched = visible
      .filter((root) => group.rootMatchers.some((m) => matchesRoot(root, m)))
      .sort((a, b) => matcherRank(a, group.rootMatchers) - matcherRank(b, group.rootMatchers));
    matched.forEach((r) => assigned.add(r.id));
    if (matched.length === 0) continue;
    resolved.push({
      id: group.id,
      label: group.label,
      highlight: Boolean(group.highlight),
      roots: matched,
      product_count: matched.reduce((sum, r) => sum + (r.product_count ?? 0), 0),
    });
  }

  // Unmatched non-empty roots append as singleton groups so nothing disappears.
  for (const root of visible) {
    if (assigned.has(root.id)) continue;
    resolved.push({
      id: `root-${root.id}`,
      label: root.name,
      highlight: false,
      roots: [root],
      product_count: root.product_count ?? 0,
    });
  }

  return resolved;
}

/** Earliest matcher index wins — keeps L1 order stable across tree vs flat APIs. */
function matcherRank(root: CategoryLike, matchers: string[]): number {
  const idx = matchers.findIndex((m) => matchesRoot(root, m));
  return idx === -1 ? Number.MAX_SAFE_INTEGER : idx;
}

/**
 * Flat L1 roots in merchandising order (Metrology first), empty nodes removed.
 * Shared by home carousel, catalog root multi-select, mobile category sheet,
 * and catalog filter L1 when no carousel root is selected.
 */
export function orderedVisibleRoots<T extends CategoryLike>(roots: T[]): T[] {
  return buildNavGroups(roots).flatMap((group) => group.roots);
}

/**
 * Taxonomy roots are parent_id == null. API depth is 1-based (roots = depth 1).
 * Never treat depth === 0 as the root signal — that was a storefront bug.
 */
export function isTaxonomyRoot(node: {
  parent_id?: number | null;
  depth?: number | null;
}): boolean {
  if (node.parent_id != null) return false;
  if (node.parent_id === null) return true;
  return node.depth === 1;
}

/**
 * Stable merchandising order for a flat list of L1 roots (same as home/carousel).
 * Non-roots are left in input order after the ordered roots.
 */
export function sortByNavOrder<T extends CategoryLike>(items: T[]): T[] {
  const rootItems = items.filter((item) =>
    isTaxonomyRoot(item as T & { parent_id?: number | null; depth?: number | null }),
  );
  if (rootItems.length === 0) return items;

  const orderedRoots = orderedVisibleRoots(rootItems);
  const orderedIds = new Set(orderedRoots.map((r) => r.id));
  const rest = items.filter((item) => !orderedIds.has(item.id));
  return [...orderedRoots, ...rest];
}

/** Whether a root belongs to the highlighted Metrology merchandising group. */
export function isMetrologyRoot(root: CategoryLike): boolean {
  const group = NAV_GROUPS.find((g) => g.highlight);
  if (!group) return false;
  return group.rootMatchers.some((m) => matchesRoot(root, m));
}
