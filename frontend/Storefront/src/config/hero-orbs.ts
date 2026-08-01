/**
 * Hero category dock — marketing overlay + live L1 tree helpers.
 * Category list always comes from DB layer-1; this file only adds images/copy/featured order.
 */

import {
  CATEGORY_ICON_BY_SLUG,
  isCategoryIconUrl,
  resolveCategoryIconUrl,
} from "@/config/category-icons";

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
  /** Featured dock order 0–5; null = only in “all categories” overlay */
  featuredOrder: number | null;
  /** Slug hint for href fallback */
  slugHint: string;
  /** Live category id when built from tree */
  categoryId?: number;
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
}

const DEFAULT_HERO_IMAGE = "/images/hero/hero-cutting-left.jpg";

/** Canonical marketing overlay for the 12 hero L1 categories. */
export const HERO_ORB_MARKETING: HeroOrbMarketing[] = [
  {
    key: "metrology",
    icon: CATEGORY_ICON_BY_SLUG["andaze-giri"]!,
    heroImage: "/images/hero/hero-metrology-left.jpg",
    subtitle:
      "کولیس، میکرومتر و گیج‌های صنعتی از برندهای معتبر — کنترل کیفیت مطمئن برای خط تولید شما",
    ctaLabel: "مشاهده اندازه‌گیری",
    featuredOrder: 0,
    slugHint: "andaze-giri",
    aliases: [
      "اندازه‌گیری",
      "اندازه گیری",
      "اندازه گیری دقیق",
      "اندازه‌گیری دقیق",
      "اندازه گیری آزمایشگاهی",
      "اندازه گیری فرز CNC",
    ],
  },
  {
    key: "insert-tools",
    icon: CATEGORY_ICON_BY_SLUG["abzar-inserti"]!,
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle: "هلدر و سیستم‌های اینسرتی برای براده‌برداری پایدار و تعویض سریع",
    ctaLabel: "ورود",
    featuredOrder: 1,
    slugHint: "abzar-inserti",
    aliases: ["ابزار اینسرتی"],
  },
  {
    key: "inserts",
    icon: CATEGORY_ICON_BY_SLUG.insert!,
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle:
      "اینسرت‌های پوشش‌دار برای سطوح برش متنوع — تعویض سریع، عمر طولانی، کیفیت ثابت",
    ctaLabel: "مشاهده اینسرت",
    featuredOrder: 2,
    slugHint: "insert",
    aliases: ["اینسرت"],
  },
  {
    key: "endmills",
    icon: CATEGORY_ICON_BY_SLUG["farz-angoshti"]!,
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle:
      "ابزارهای پروفایل و فرز انگشتی برای ماشین‌کاری تمیز — از کاربید تا پوشش‌های پیشرفته",
    ctaLabel: "مشاهده فرز انگشتی",
    featuredOrder: 3,
    slugHint: "farz-angoshti",
    aliases: ["فرز انگشتی", "ابزار انگشتی"],
  },
  {
    key: "taps",
    icon: CATEGORY_ICON_BY_SLUG.ghalaviz!,
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle: "قلاویز دستی و ماشینی برای رزوه‌کاری استاندارد صنعتی",
    ctaLabel: "ورود",
    featuredOrder: null,
    slugHint: "ghalaviz",
    aliases: ["قلاویز"],
  },
  {
    key: "toolholders",
    icon: CATEGORY_ICON_BY_SLUG["abzar-gir"]!,
    heroImage: "/images/hero/hero-holding-left.jpg",
    subtitle: "هولدر و رابط‌های ابزار برای پایداری بیشتر در اسپیندل",
    ctaLabel: "ورود",
    featuredOrder: null,
    slugHint: "abzar-gir",
    aliases: ["ابزار گیر", "ابزارگیر"],
  },
  {
    key: "workholding",
    icon: CATEGORY_ICON_BY_SLUG["abzar-gireshi"]!,
    heroImage: "/images/hero/hero-holding-left.jpg",
    subtitle:
      "گیره، فیکسچر و سیستم‌های نگه‌دارنده — ثبات بیشتر، لرزش کمتر، نتیجه تمیزتر در ماشین‌کاری",
    ctaLabel: "مشاهده ابزار گیرشی",
    featuredOrder: 4,
    slugHint: "abzar-gireshi",
    aliases: ["ابزار گیرشی"],
  },
  {
    key: "industrial-machines",
    icon: CATEGORY_ICON_BY_SLUG["dastgah-sanati"]!,
    heroImage: "/images/hero/hero-machines-left.jpg",
    subtitle:
      "ماشین‌ها و تجهیزات صنعتی برای ارتقای ظرفیت کارگاه — انتخاب تخصصی، پشتیبانی کارزاری",
    ctaLabel: "مشاهده دستگاه‌ها",
    featuredOrder: 5,
    slugHint: "dastgah-sanati",
    aliases: ["دستگاه‌های صنعتی", "دستگاه های صنعتی"],
  },
  {
    key: "heli-coil",
    icon: CATEGORY_ICON_BY_SLUG["heli-coil"]!,
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle: "فنر، قلاویز و کیت‌های هلی‌کویل برای ترمیم رزوه",
    ctaLabel: "ورود",
    featuredOrder: null,
    slugHint: "heli-coil",
    aliases: ["هلی کویل", "هلی‌کویل"],
  },
  {
    key: "drills",
    icon: CATEGORY_ICON_BY_SLUG.mete!,
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle: "مته‌های HSS و کاربید برای سوراخ‌کاری تمیز و تکرارپذیر",
    ctaLabel: "ورود",
    featuredOrder: null,
    slugHint: "mete",
    aliases: ["مته"],
  },
  {
    key: "workshop-tools",
    icon: CATEGORY_ICON_BY_SLUG["abzar-kargahi"]!,
    heroImage: "/images/hero/hero-holding-left.jpg",
    subtitle: "ابزار کارگاهی و دریل عادی برای کار روزمره کارگاه",
    ctaLabel: "ورود",
    featuredOrder: null,
    slugHint: "abzar-kargahi",
    aliases: ["ابزار کارگاهی : دریل عادی", "ابزار کارگاهی"],
  },
  {
    key: "lubricants",
    icon: CATEGORY_ICON_BY_SLUG["roghan-ravankar"]!,
    heroImage: "/images/hero/hero-accessories-left.jpg",
    subtitle: "روغن برش و روانکار صنعتی برای طول عمر ابزار و کیفیت سطح",
    ctaLabel: "ورود",
    featuredOrder: null,
    slugHint: "roghan-ravankar",
    aliases: ["روغن و روانکار", "روغن و زوانکار", "لوازم جانبی صنعتی"],
  },
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
  Pick<HeroOrbDef, "heroImage" | "subtitle" | "ctaLabel" | "featuredOrder" | "icon">
> & { key?: string; name?: string };

/**
 * Build hero orb defs from live L1 roots. Marketing overlay fills images/copy/featured.
 * Optional published dock overrides featured order / images by name or key.
 */
export function orbsFromRoots(
  roots: TreeRootLike[],
  dockOverrides?: DockOverride[] | null,
): HeroOrbDef[] {
  if (!roots.length) return [];

  const byKey = new Map<string, DockOverride>();
  const byName = new Map<string, DockOverride>();
  for (const row of dockOverrides ?? []) {
    if (row.key) byKey.set(row.key, row);
    if (row.name) byName.set(normalizeFa(row.name), row);
  }

  const hasDock = (dockOverrides?.length ?? 0) > 0;

  return roots.map((root) => {
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
};

/**
 * Prefer the published admin dock as the source of truth for which orbs exist
 * and which 6 are featured. Enrich with live L1 ids/counts when available.
 */
export function orbsFromPublishedDock(
  dockCategories: PublishedDockCategory[],
  roots: TreeRootLike[] = [],
): HeroOrbDef[] {
  if (!dockCategories.length) return [];

  const byId = new Map(roots.map((r) => [r.id, r]));
  const byName = new Map(roots.map((r) => [normalizeFa(r.name), r]));

  return dockCategories.map((cat) => {
    const root =
      (cat.categoryId != null ? byId.get(cat.categoryId) : undefined) ??
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
    };
  });
}

export function featuredOrbs(defs: HeroOrbDef[] = HERO_ORB_CATEGORIES): HeroOrbDef[] {
  return [...defs]
    .filter((d) => d.featuredOrder != null)
    .sort((a, b) => (a.featuredOrder ?? 0) - (b.featuredOrder ?? 0))
    .slice(0, 6);
}

export function matchOrbToTreeNode<T extends { name: string; slug?: string | null; id: number }>(
  orb: HeroOrbDef,
  roots: T[],
): T | undefined {
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
  if (node?.slug) return `/categories/${node.slug}`;
  if (orb.slugHint) return `/categories/${orb.slugHint}`;
  if (node?.id) return `/catalog?category=${node.id}`;
  if (orb.categoryId) return `/catalog?category=${orb.categoryId}`;
  return `/catalog?q=${encodeURIComponent(orb.name)}`;
}
