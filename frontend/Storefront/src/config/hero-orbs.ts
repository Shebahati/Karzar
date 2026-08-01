/**
 * Hero category dock — marketing overlay + live L1 tree helpers.
 * Canonical L1 list: `final-l1-categories.ts`. This file maps marketing + live tree.
 * Special dock member `discounts` (تخفیف‌ها) is not an L1 DB category.
 */

import {
  CATEGORY_ICON_BY_SLUG,
  isCategoryIconUrl,
  resolveCategoryIconUrl,
} from "@/config/category-icons";
import {
  DISCOUNTS_CATALOG_HREF,
  DISCOUNTS_ORB_KEY,
  DISCOUNTS_SPECIAL,
  FINAL_L1_CATEGORIES,
} from "@/config/final-l1-categories";

export { DISCOUNTS_CATALOG_HREF, DISCOUNTS_ORB_KEY };

/** Featured power slots on the storefront dock (RTL order 0 = rightmost). */
export const HERO_FEATURED_SLOT_COUNT = 5;

export interface HeroOrbDef {
  key: string;
  name: string;
  /** Iconly export name OR image URL under /category-icons/ */
  icon: string;
  /** Display count for marketing surfaces */
  productCount: number;
  /** Full-bleed hero photo (left-weighted packshots) */
  heroImage: string;
  /** Elegant one-liner under the hero title */
  subtitle: string;
  /** Short CTA label */
  ctaLabel: string;
  /** Featured dock order 0–4; null = only in “all categories” overlay */
  featuredOrder: number | null;
  /** Slug hint for href fallback */
  slugHint: string;
  /** Live category id when built from tree */
  categoryId?: number;
  /** Non-L1 special dock member (e.g. discounts) */
  special?: boolean;
}

/** Marketing extras keyed by Persian L1 name (not a category source of truth). */
export interface HeroOrbMarketing {
  key: string;
  icon: string;
  heroImage: string;
  subtitle: string;
  ctaLabel: string;
  featuredOrder: number | null;
  slugHint: string;
  /** Alternate DB names that should reuse this marketing pack */
  aliases?: string[];
  special?: boolean;
}

const DEFAULT_HERO_IMAGE = "/images/hero/hero-cutting-left.jpg";

/** Special dock orb — تخفیف‌ها (first from the right / featuredOrder 0). */
export const DISCOUNTS_ORB_MARKETING: HeroOrbMarketing = {
  key: DISCOUNTS_SPECIAL.key,
  icon: CATEGORY_ICON_BY_SLUG[DISCOUNTS_SPECIAL.iconSlug]!,
  heroImage: DISCOUNTS_SPECIAL.heroImage,
  subtitle: DISCOUNTS_SPECIAL.subtitle,
  ctaLabel: DISCOUNTS_SPECIAL.ctaLabel,
  featuredOrder: DISCOUNTS_SPECIAL.featuredOrder,
  slugHint: DISCOUNTS_SPECIAL.slug,
  aliases: DISCOUNTS_SPECIAL.aliases,
  special: true,
};

export function isDiscountsOrbKey(key?: string | null): boolean {
  return key === DISCOUNTS_ORB_KEY || key === "takhfif";
}

export function discountsHeroOrb(): HeroOrbDef {
  const m = DISCOUNTS_ORB_MARKETING;
  return {
    key: m.key,
    name: m.aliases?.[0] ?? "تخفیف‌ها",
    icon: m.icon,
    productCount: 0,
    heroImage: m.heroImage,
    subtitle: m.subtitle,
    ctaLabel: m.ctaLabel,
    featuredOrder: m.featuredOrder,
    slugHint: m.slugHint,
    special: true,
  };
}

/** Canonical marketing overlay for hero L1 categories (+ special discounts). */
export const HERO_ORB_MARKETING: HeroOrbMarketing[] = [
  DISCOUNTS_ORB_MARKETING,
  ...FINAL_L1_CATEGORIES.map((c) => ({
    key: c.key,
    icon: CATEGORY_ICON_BY_SLUG[c.iconSlug] ?? CATEGORY_ICON_BY_SLUG[c.slug] ?? "Category",
    heroImage: c.heroImage,
    subtitle: c.subtitle,
    ctaLabel: c.ctaLabel,
    featuredOrder: c.featuredOrder,
    slugHint: c.slug,
    aliases: c.aliases ?? [c.name],
  })),
];

/** @deprecated Prefer `orbsFromRoots` — kept as marketing-shaped fallback when tree is empty. */
export const HERO_ORB_CATEGORIES: HeroOrbDef[] = HERO_ORB_MARKETING.map((m) => ({
  key: m.key,
  name: m.aliases?.[0] ?? m.key,
  icon: m.icon,
  productCount: 0,
  heroImage: m.heroImage,
  subtitle: m.subtitle,
  ctaLabel: m.ctaLabel,
  featuredOrder: m.featuredOrder,
  slugHint: m.slugHint,
  special: m.special,
}));

function normalizeFa(s: string): string {
  return s.trim().replace(/\u200c/g, "").replace(/ي/g, "ی").replace(/ك/g, "ک").toLowerCase();
}

export function findOrbMarketing(name: string, slug?: string | null): HeroOrbMarketing | undefined {
  const target = normalizeFa(name);
  const slugN = normalizeFa(slug ?? "");
  return HERO_ORB_MARKETING.find((m) => {
    const names = [m.key, ...(m.aliases ?? [])].map(normalizeFa);
    return (
      names.some((n) => n === target || target.includes(n) || n.includes(target)) ||
      (slugN && slugN.includes(normalizeFa(m.slugHint)))
    );
  });
}

type TreeRootLike = {
  id: number;
  name: string;
  slug?: string | null;
  icon?: string | null;
  product_count?: number | null;
};

type DockOverride = Partial<
  Pick<HeroOrbDef, "heroImage" | "subtitle" | "ctaLabel" | "featuredOrder" | "icon" | "special">
> & { key?: string; name?: string };

function injectDiscountsOrb(
  orbs: HeroOrbDef[],
  dockOverrides?: DockOverride[] | null,
): HeroOrbDef[] {
  if (orbs.some((o) => isDiscountsOrbKey(o.key))) return orbs;
  const override =
    dockOverrides?.find((r) => isDiscountsOrbKey(r.key ?? "")) ??
    dockOverrides?.find((r) => r.name && normalizeFa(r.name).includes("تخفیف"));
  const base = discountsHeroOrb();
  return [
    {
      ...base,
      ...(override ?? {}),
      key: DISCOUNTS_ORB_KEY,
      name: override?.name || base.name,
      icon: override?.icon || base.icon,
      featuredOrder:
        override?.featuredOrder !== undefined ? override.featuredOrder : base.featuredOrder,
      special: true,
    },
    ...orbs,
  ];
}

/**
 * Build hero orb defs from live L1 roots. Marketing overlay fills images/copy/featured.
 * Optional published dock overrides featured order / images by name or key.
 * Always injects the special discounts orb when missing.
 */
export function orbsFromRoots(
  roots: TreeRootLike[],
  dockOverrides?: DockOverride[] | null,
): HeroOrbDef[] {
  if (!roots.length) return injectDiscountsOrb([], dockOverrides);

  const byKey = new Map<string, DockOverride>();
  const byName = new Map<string, DockOverride>();
  for (const row of dockOverrides ?? []) {
    if (row.key) byKey.set(row.key, row);
    if (row.name) byName.set(normalizeFa(row.name), row);
  }

  const hasDock = (dockOverrides?.length ?? 0) > 0;

  const fromRoots = roots.map((root) => {
    const marketing = findOrbMarketing(root.name, root.slug);
    const key = marketing?.key ?? root.slug ?? `cat-${root.id}`;
    const override = byKey.get(key) ?? byName.get(normalizeFa(root.name));
    const resolvedIcon =
      (override?.icon && (isCategoryIconUrl(override.icon) || override.icon)
        ? override.icon
        : null) ||
      resolveCategoryIconUrl(root) ||
      marketing?.icon ||
      "Category";

    return {
      key,
      name: root.name,
      icon: resolvedIcon,
      productCount: root.product_count ?? 0,
      heroImage: override?.heroImage || marketing?.heroImage || DEFAULT_HERO_IMAGE,
      subtitle:
        override?.subtitle ||
        marketing?.subtitle ||
        `محصولات دسته «${root.name}» در فروشگاه کارزار`,
      ctaLabel: override?.ctaLabel || marketing?.ctaLabel || "ورود",
      featuredOrder: hasDock
        ? (override?.featuredOrder ?? null)
        : override?.featuredOrder !== undefined
          ? override.featuredOrder
          : (marketing?.featuredOrder ?? null),
      slugHint: root.slug ?? marketing?.slugHint ?? "",
      categoryId: root.id,
    };
  });

  return injectDiscountsOrb(fromRoots, dockOverrides);
}

type PublishedDockCategory = {
  key: string;
  name: string;
  icon: string;
  productCount: number;
  heroImage: string;
  subtitle: string;
  ctaLabel: string;
  featuredOrder: number | null;
  slugHint: string;
  categoryId?: number;
  special?: boolean;
};

/**
 * Prefer the published admin dock as the source of truth for which orbs exist
 * and which 5 are featured. Enrich with live L1 ids/counts when available.
 */
export function orbsFromPublishedDock(
  dockCategories: PublishedDockCategory[],
  roots: TreeRootLike[] = [],
): HeroOrbDef[] {
  if (!dockCategories.length) return [];

  const byId = new Map(roots.map((r) => [r.id, r]));
  const byName = new Map(roots.map((r) => [normalizeFa(r.name), r]));

  const mapped = dockCategories.map((cat) => {
    const special = Boolean(cat.special) || isDiscountsOrbKey(cat.key);
    const root = special
      ? undefined
      : (cat.categoryId != null ? byId.get(cat.categoryId) : undefined) ??
        byName.get(normalizeFa(cat.name));
    return {
      key: cat.key,
      name: root?.name ?? cat.name,
      icon:
        cat.icon ||
        resolveCategoryIconUrl(root ?? cat) ||
        "Category",
      productCount: root?.product_count ?? cat.productCount ?? 0,
      heroImage: cat.heroImage || DEFAULT_HERO_IMAGE,
      subtitle: cat.subtitle,
      ctaLabel: cat.ctaLabel || "ورود",
      featuredOrder: cat.featuredOrder ?? null,
      slugHint: root?.slug ?? cat.slugHint ?? "",
      categoryId: root?.id ?? cat.categoryId,
      special,
    };
  });

  return injectDiscountsOrb(mapped, dockCategories);
}

export function featuredOrbs(defs: HeroOrbDef[] = HERO_ORB_CATEGORIES): HeroOrbDef[] {
  return [...defs]
    .filter((d) => d.featuredOrder != null)
    .sort((a, b) => (a.featuredOrder ?? 0) - (b.featuredOrder ?? 0))
    .slice(0, HERO_FEATURED_SLOT_COUNT);
}

export function matchOrbToTreeNode<T extends { name: string; slug?: string | null; id: number }>(
  orb: HeroOrbDef,
  roots: T[],
): T | undefined {
  if (orb.special || isDiscountsOrbKey(orb.key)) return undefined;
  if (orb.categoryId != null) {
    const byId = roots.find((r) => r.id === orb.categoryId);
    if (byId) return byId;
  }
  const target = normalizeFa(orb.name);
  return roots.find((r) => {
    const name = normalizeFa(r.name);
    const slug = normalizeFa(r.slug ?? "");
    return (
      name === target ||
      name.includes(target) ||
      target.includes(name) ||
      (orb.slugHint && slug.includes(normalizeFa(orb.slugHint)))
    );
  });
}

export function orbHref(
  orb: HeroOrbDef,
  node?: { id: number; slug?: string | null } | null,
): string {
  if (orb.special || isDiscountsOrbKey(orb.key) || orb.slugHint === "takhfif") {
    return DISCOUNTS_CATALOG_HREF;
  }
  if (node?.slug) return `/categories/${node.slug}`;
  if (orb.slugHint) return `/categories/${orb.slugHint}`;
  if (node?.id) return `/catalog?category=${node.id}`;
  if (orb.categoryId) return `/catalog?category=${orb.categoryId}`;
  return `/catalog?search=${encodeURIComponent(orb.name)}`;
}
