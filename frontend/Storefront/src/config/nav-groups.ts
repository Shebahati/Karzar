/**
 * Merchandising display groups over taxonomy roots (FE-only; taxonomy stays 10 roots).
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
    const matched = visible.filter((root) =>
      group.rootMatchers.some((m) => matchesRoot(root, m)),
    );
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
