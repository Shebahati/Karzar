/**
 * Category helpers shared by storefront browse surfaces.
 *
 * Locked IA:
 * - Commerce SoR = product-type tree, depth ≤ 3
 * - Brand / country = facets (not categories)
 * - **All category UIs (megamenu, home, catalog, mobile) = live L1 from GET /categories/tree**
 *   via `orderedTaxonomyRoots` (sorted by FINAL_L1_CATEGORIES merchandising order).
 *
 * `NAV_GROUPS` / `buildNavGroups` remain only as legacy fallback for older tests;
 * megamenu no longer consumes them.
 */

import { FINAL_L1_CATEGORIES } from "@/config/l1-categories";

export interface NavGroupDef {
  id: string;
  label: string;
  /** Highlight Metrology in menus. */
  highlight?: boolean;
  /** Match roots by exact name (Persian) or slug substring (fallback path). */
  rootMatchers?: string[];
  /** Preferred: ordered Layer-1 category IDs from admin/API config. */
  rootCategoryIds?: number[];
}

/** API row shape from GET /nav-groups/ */
export interface NavGroupApiRow {
  id: number;
  slug: string;
  label: string;
  sort_order: number;
  highlight?: boolean;
  root_category_ids: number[];
}

export const NAV_GROUPS: NavGroupDef[] = [
  {
    id: "metrology",
    label: "اندازه‌گیری",
    highlight: true,
    rootMatchers: [
      "اندازه گیری دقیق",
      "اندازه گیری آزمایشگاهی",
      "اندازه گیری فرز CNC",
      "CNC اندازه گیری",
      "اندازه گیری",
      "اندازه‌گیری",
      "andaze",
      "measurement",
    ],
  },
  {
    id: "cutting",
    label: "براده‌برداری",
    rootMatchers: [
      "ابزار انگشتی",
      "ابزار اینسرتی",
      "ابزار تراشکاری",
      "اینسرت",
      "فرز انگشتی",
      "انگشتی",
      "مته‌ها",
      "مته",
      "قلاویز",
      "insert",
    ],
  },
  {
    id: "holding",
    label: "ابزارگیری و گیرش",
    rootMatchers: ["ابزارگیر", "ابزار گیر", "ابزار گیرشی"],
  },
  {
    id: "machines",
    label: "ماشین‌ها و تجهیزات",
    rootMatchers: ["دستگاه‌های صنعتی", "دستگاه های صنعتی"],
  },
  {
    id: "accessories",
    label: "لوازم جانبی",
    rootMatchers: ["لوازم جانبی صنعتی", "لوازم جانبی", "روغن و روانکار"],
  },
];

/** Map API rows → NavGroupDef; empty input → empty (caller uses NAV_GROUPS fallback). */
export function navGroupsFromApi(rows: NavGroupApiRow[] | null | undefined): NavGroupDef[] {
  if (!rows?.length) return [];
  return [...rows]
    .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
    .map((row) => ({
      id: row.slug,
      label: row.label,
      highlight: Boolean(row.highlight),
      rootCategoryIds: [...(row.root_category_ids ?? [])],
    }));
}

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

function rootsForGroup<T extends CategoryLike>(visible: T[], group: NavGroupDef): T[] {
  if (group.rootCategoryIds && group.rootCategoryIds.length > 0) {
    const byId = new Map(visible.map((root) => [root.id, root]));
    return group.rootCategoryIds
      .map((id) => byId.get(id))
      .filter((root): root is T => Boolean(root));
  }
  const matchers = group.rootMatchers ?? [];
  return visible
    .filter((root) => matchers.some((m) => matchesRoot(root, m)))
    .sort((a, b) => matcherRank(a, matchers) - matcherRank(b, matchers));
}

export function buildNavGroups<T extends CategoryLike>(
  roots: T[],
  groups: NavGroupDef[] = NAV_GROUPS,
): ResolvedNavGroup<T>[] {
  const visible = filterNonEmptyTree(roots);
  const assigned = new Set<number>();
  const resolved: ResolvedNavGroup<T>[] = [];

  for (const group of groups) {
    const matched = rootsForGroup(visible, group);
    matched.forEach((r) => assigned.add(r.id));
    // Hide empty groups (no member roots with products) — storefront preference.
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
 * Shared by home carousel, catalog root carousel, mobile category sheet,
 * and catalog filter L1 when no carousel root is selected.
 */
export function orderedVisibleRoots<T extends CategoryLike>(
  roots: T[],
  groups: NavGroupDef[] = NAV_GROUPS,
): T[] {
  return buildNavGroups(roots, groups).flatMap((group) => group.roots);
}

/**
 * All taxonomy L1 roots in **FINAL_L1_CATEGORIES merchandising order**.
 * Unknown / unmatched roots keep relative order at the end.
 * `_groups` kept for call-site compatibility; intentionally unused.
 */
export function orderedTaxonomyRoots<T extends CategoryLike>(
  roots: T[],
  _groups?: NavGroupDef[],
): T[] {
  const rank = (root: CategoryLike): number => {
    const idx = FINAL_L1_CATEGORIES.findIndex(
      (c) =>
        c.name === root.name ||
        c.slug === root.slug ||
        (c.aliases ?? []).some((a) => matchesRoot(root, a)),
    );
    return idx === -1 ? Number.MAX_SAFE_INTEGER : idx;
  };
  return roots.slice().sort((a, b) => {
    const diff = rank(a) - rank(b);
    return diff !== 0 ? diff : a.id - b.id;
  });
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
export function sortByNavOrder<T extends CategoryLike>(
  items: T[],
  groups: NavGroupDef[] = NAV_GROUPS,
): T[] {
  const rootItems = items.filter((item) =>
    isTaxonomyRoot(item as T & { parent_id?: number | null; depth?: number | null }),
  );
  if (rootItems.length === 0) return items;

  const orderedRoots = orderedVisibleRoots(rootItems, groups);
  const orderedIds = new Set(orderedRoots.map((r) => r.id));
  const rest = items.filter((item) => !orderedIds.has(item.id));
  return [...orderedRoots, ...rest];
}

/** Whether a root belongs to the highlighted Metrology merchandising group. */
export function isMetrologyRoot(root: CategoryLike, groups: NavGroupDef[] = NAV_GROUPS): boolean {
  const group = groups.find((g) => g.highlight);
  if (!group) return false;
  if (group.rootCategoryIds?.length) {
    return group.rootCategoryIds.includes(root.id);
  }
  return (group.rootMatchers ?? []).some((m) => matchesRoot(root, m));
}
