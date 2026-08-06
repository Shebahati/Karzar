import {
  DISCOUNTS_CATALOG_HREF,
  DISCOUNTS_ORB_KEY,
  DISCOUNTS_SPECIAL,
  FINAL_L1_CATEGORIES,
} from "@/config/l1-categories";
import { CATEGORY_ICON_BY_SLUG } from "@/config/category-icons";
import type {
  HeroAnimationPreset,
  HeroBadgeKind,
  HeroBadgeStyle,
  HeroBuilderConfig,
  HeroCategoryDock,
  HeroDesignProject,
  HeroOrbCategory,
  HeroSlideDraft,
} from "./types";
import { curatedSlidesFromDock } from "./curated-slides";

export const HERO_ANIMATION_PRESETS: {
  id: HeroAnimationPreset;
  label: string;
  description: string;
}[] = [
  { id: "none", label: "بدون انیمیشن", description: "ثابت و فوری" },
  { id: "fade-up", label: "محو از پایین", description: "نرم و حرفه‌ای" },
  { id: "fade-in", label: "ظهور آرام", description: "ساده و شیک" },
  { id: "slide-in", label: "اسلاید RTL", description: "ورود از سمت راست" },
  { id: "zoom-soft", label: "زوم نرم", description: "بزرگ‌نمایی ملایم" },
  { id: "float", label: "شناور", description: "حرکت آرام عمودی" },
  { id: "stagger-up", label: "پله‌ای", description: "متن و دکمه‌ها به‌ترتیب" },
];

export const HERO_BADGE_KINDS: {
  id: HeroBadgeKind;
  label: string;
  defaultLabel: string;
  defaultMeta?: string;
}[] = [
  { id: "discount", label: "تخفیف", defaultLabel: "تخفیف ویژه", defaultMeta: "تا ۲۵٪" },
  { id: "flash_sale", label: "فروش ویژه", defaultLabel: "فروش ویژه", defaultMeta: "امروز" },
  { id: "campaign", label: "کمپین", defaultLabel: "کمپین بهاره", defaultMeta: "۱۴۰۵" },
  { id: "new_arrival", label: "جدید", defaultLabel: "تازه رسیده", defaultMeta: "NEW" },
  { id: "limited", label: "محدود", defaultLabel: "موجودی محدود", defaultMeta: "فقط چند عدد" },
  { id: "free_shipping", label: "ارسال رایگان", defaultLabel: "ارسال رایگان", defaultMeta: "تهران" },
  { id: "trust", label: "اعتماد", defaultLabel: "اصالت کالا", defaultMeta: "گارانتی" },
];

export const HERO_BADGE_STYLES: { id: HeroBadgeStyle; label: string }[] = [
  { id: "pill", label: "قرصی" },
  { id: "ribbon", label: "روبان" },
  { id: "chip", label: "چیپ شیشه‌ای" },
  { id: "banner", label: "نوار" },
  { id: "stamp", label: "مهر" },
];

export const BRAND_COLOR_PRESETS = [
  "#D02327",
  "#A41A1F",
  "#7A1216",
  "#FCEAEB",
  "#FF6B6B",
  "#5E5F5E",
  "#3F4040",
  "#1A1A1A",
  "#000000",
  "#FFFFFF",
  "#F5F5F5",
  "#E8E8E8",
  "#C4A574",
  "#1F6F4A",
  "#2F9E68",
  "#B45309",
  "#D97706",
  "#1E3A5F",
  "#3B82A8",
  "#7C3AED",
  "#DB2777",
  "#0EA5E9",
  "#F59E0B",
  "#10B981",
] as const;

export function createId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 9)}`;
}

/** Featured power slots on the storefront dock (RTL: 0 = rightmost). */
export const HERO_FEATURED_SLOT_COUNT = 5;

/** Fixed carousel length — publish requires exactly this many filled slides. */
export const HERO_SLIDE_SLOT_COUNT = 6;

export { DISCOUNTS_ORB_KEY, DISCOUNTS_CATALOG_HREF };

export type HeroProjectIssue = {
  code:
    | "slide_count"
    | "slide_empty"
    | "dock_featured"
    | "dock_collision"
    | "duplicate_link";
  message: string;
};

/** Clamp + dedupe featuredOrder into sparse slots 0..(FEATURED-1). */
export function densifyFeaturedOrders(
  categories: HeroOrbCategory[],
): HeroOrbCategory[] {
  const claimed = new Map<number, string>();
  const maxSlot = HERO_FEATURED_SLOT_COUNT - 1;
  return categories.map((c) => {
    if (c.featuredOrder == null) return { ...c, featuredOrder: null };
    const slot = Math.max(0, Math.min(maxSlot, Math.floor(c.featuredOrder)));
    if (claimed.has(slot)) return { ...c, featuredOrder: null };
    claimed.set(slot, c.key);
    return { ...c, featuredOrder: slot };
  });
}

export function firstEmptyFeaturedSlot(
  categories: HeroOrbCategory[],
): number | null {
  const used = new Set(
    categories
      .map((c) => c.featuredOrder)
      .filter((n): n is number => n != null),
  );
  for (let i = 0; i < HERO_FEATURED_SLOT_COUNT; i++) {
    if (!used.has(i)) return i;
  }
  return null;
}

/** One slide ↔ one orb key. Later duplicates lose the link. */
export function dedupeSlideOrbLinks(slides: HeroSlideDraft[]): HeroSlideDraft[] {
  const seen = new Set<string>();
  return slides.map((slide) => {
    const key = slide.config.linkedOrbKey;
    if (!key || slide.isPlaceholder) return slide;
    if (seen.has(key)) {
      return {
        ...slide,
        config: { ...slide.config, linkedOrbKey: null },
      };
    }
    seen.add(key);
    return slide;
  });
}

export function createEmptySlideSlot(slotIndex: number): HeroSlideDraft {
  return {
    id: createId("slide"),
    name: `اسلات ${slotIndex + 1}`,
    sortOrder: slotIndex + 1,
    isActive: false,
    isPlaceholder: true,
    mobilePreset: "balanced",
    config: createDefaultConfig(),
  };
}

export function isSlideFilled(slide: HeroSlideDraft): boolean {
  if (slide.isPlaceholder) return false;
  const title = slide.config.typography.title?.trim();
  const hasBg =
    slide.config.background.mode === "color" ||
    Boolean(slide.config.background.imageUrl?.trim());
  return Boolean(title) && hasBg;
}

/**
 * Always exactly 6 slots. Keep stable ids when possible.
 * Truncate overflow by sortOrder; pad empties; dedupe orb links.
 */
export function normalizeHeroSlides(
  slides: HeroSlideDraft[] | undefined,
  mobilePreset: HeroDesignProject["mobilePreset"] = "balanced",
): HeroSlideDraft[] {
  const sorted = [...(slides ?? [])].sort((a, b) => a.sortOrder - b.sortOrder);
  const kept: HeroSlideDraft[] = sorted.slice(0, HERO_SLIDE_SLOT_COUNT).map((slide, i) => ({
    ...slide,
    sortOrder: i + 1,
    mobilePreset: slide.mobilePreset ?? mobilePreset,
    isPlaceholder: slide.isPlaceholder === true ? true : false,
    config: {
      ...slide.config,
      linkedOrbKey: slide.isPlaceholder ? null : (slide.config.linkedOrbKey ?? null),
    },
  }));
  while (kept.length < HERO_SLIDE_SLOT_COUNT) {
    kept.push(createEmptySlideSlot(kept.length));
  }
  return dedupeSlideOrbLinks(kept);
}

export function normalizeHeroProject(project: HeroDesignProject): HeroDesignProject {
  const dockCats = densifyFeaturedOrders(
    project.categoryDock?.categories ?? DEFAULT_CATEGORY_DOCK.categories,
  );
  // Discounts stay featured at slot 0 when present.
  const withDiscounts = dockCats.map((c) => {
    if (!isSpecialDockOrb(c)) return c;
    return {
      ...c,
      featuredOrder: c.featuredOrder == null ? 0 : c.featuredOrder,
      special: true as const,
      key: DISCOUNTS_ORB_KEY,
    };
  });
  const slides = normalizeHeroSlides(project.slides, project.mobilePreset);
  const activeSlideId = slides.some((s) => s.id === project.activeSlideId)
    ? project.activeSlideId
    : slides[0]!.id;
  return {
    ...project,
    activeSlideId,
    slides,
    categoryDock: { categories: withDiscounts },
    mobilePreset: project.mobilePreset ?? "balanced",
  };
}

/** Persian validation for publish / UI banners. */
export function validateHeroProject(project: HeroDesignProject): HeroProjectIssue[] {
  const issues: HeroProjectIssue[] = [];
  const slides = normalizeHeroSlides(project.slides, project.mobilePreset);
  const filled = slides.filter(isSlideFilled);

  if (slides.length !== HERO_SLIDE_SLOT_COUNT) {
    issues.push({
      code: "slide_count",
      message: `هیرو باید دقیقاً ${HERO_SLIDE_SLOT_COUNT} اسلاید داشته باشد (الان ${slides.length}).`,
    });
  }
  if (filled.length < HERO_SLIDE_SLOT_COUNT) {
    issues.push({
      code: "slide_empty",
      message: `${HERO_SLIDE_SLOT_COUNT - filled.length} اسلات اسلاید خالی است — هر ۶ اسلات را پر کنید.`,
    });
  }

  const dock = project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
  const featured = featuredDockCategories(dock);
  if (featured.length < HERO_FEATURED_SLOT_COUNT) {
    issues.push({
      code: "dock_featured",
      message: `داک پاور ناقص است (${featured.length}/${HERO_FEATURED_SLOT_COUNT}).`,
    });
  }

  const orders = dock.categories
    .map((c) => c.featuredOrder)
    .filter((n): n is number => n != null);
  if (new Set(orders).size !== orders.length) {
    issues.push({
      code: "dock_collision",
      message: "دو دسته روی یک اسلات پاور نشسته‌اند — ترتیب داک را اصلاح کنید.",
    });
  }

  const keys = slides
    .map((s) => s.config.linkedOrbKey)
    .filter((k): k is string => Boolean(k));
  if (new Set(keys).size !== keys.length) {
    issues.push({
      code: "duplicate_link",
      message: "چند اسلاید به یک دسته وصل شده‌اند — هر دسته فقط یک اسلاید.",
    });
  }

  return issues;
}

/** Find featured dock index for a slide via stable orb key (never array index). */
export function featuredIndexForSlide(
  slide: HeroSlideDraft | undefined,
  dock: HeroCategoryDock = DEFAULT_CATEGORY_DOCK,
): number {
  const key = slide?.config.linkedOrbKey;
  if (!key) return -1;
  const featured = featuredDockCategories(dock);
  return featured.findIndex((o) => o.key === key);
}

/** Resolve slide id linked to an orb key. */
export function slideIdForOrbKey(
  slides: HeroSlideDraft[],
  orbKey: string,
): string | null {
  return slides.find((s) => !s.isPlaceholder && s.config.linkedOrbKey === orbKey)?.id ?? null;
}

export function isSpecialDockOrb(orb: Pick<HeroOrbCategory, "key" | "special" | "slugHint">): boolean {
  return (
    Boolean(orb.special) ||
    orb.key === DISCOUNTS_ORB_KEY ||
    orb.key === "takhfif" ||
    orb.slugHint === "takhfif"
  );
}

export function createDiscountsOrb(prev?: Partial<HeroOrbCategory>): HeroOrbCategory {
  return {
    key: DISCOUNTS_ORB_KEY,
    name: DISCOUNTS_SPECIAL.name,
    icon: CATEGORY_ICON_BY_SLUG[DISCOUNTS_SPECIAL.iconSlug] ?? "/category-icons/takhfif.png",
    productCount: prev?.productCount ?? 0,
    heroImage: prev?.heroImage || DISCOUNTS_SPECIAL.heroImage,
    subtitle: prev?.subtitle || DISCOUNTS_SPECIAL.subtitle,
    ctaLabel: prev?.ctaLabel || DISCOUNTS_SPECIAL.ctaLabel,
    featuredOrder: prev?.featuredOrder !== undefined ? prev.featuredOrder : DISCOUNTS_SPECIAL.featuredOrder,
    slugHint: DISCOUNTS_SPECIAL.slug,
    special: true,
  };
}

function orbFromFinalL1(cat: (typeof FINAL_L1_CATEGORIES)[number]): HeroOrbCategory {
  return {
    key: cat.key,
    name: cat.name,
    icon: CATEGORY_ICON_BY_SLUG[cat.iconSlug] ?? `/category-icons/${cat.slug}.png`,
    productCount: 0,
    heroImage: cat.heroImage,
    subtitle: cat.subtitle,
    ctaLabel: cat.ctaLabel,
    featuredOrder: cat.featuredOrder,
    slugHint: cat.slug,
  };
}

export const DEFAULT_CATEGORY_DOCK: HeroCategoryDock = {
  categories: [createDiscountsOrb(), ...FINAL_L1_CATEGORIES.map(orbFromFinalL1)],
};

export function featuredDockCategories(
  dock: HeroCategoryDock = DEFAULT_CATEGORY_DOCK,
): HeroOrbCategory[] {
  return [...dock.categories]
    .filter((c) => c.featuredOrder != null)
    .sort((a, b) => (a.featuredOrder ?? 0) - (b.featuredOrder ?? 0))
    .slice(0, HERO_FEATURED_SLOT_COUNT);
}

type TreeRootLike = {
  id: number;
  name: string;
  slug?: string | null;
  icon?: string | null;
  product_count?: number | null;
  parent_id?: number | null;
};

function normalizeFa(s: string): string {
  return s.trim().replace(/\u200c/g, "").replace(/ي/g, "ی").replace(/ك/g, "ک").toLowerCase();
}

/** Loose name match so renamed L1 roots still sync to curated dock rows. */
function namesLooselyMatch(a: string, b: string): boolean {
  const na = normalizeFa(a);
  const nb = normalizeFa(b);
  if (!na || !nb) return false;
  return na === nb || na.includes(nb) || nb.includes(na);
}

function findRootForOrb(
  orb: HeroOrbCategory,
  byId: Map<number, TreeRootLike>,
  l1: TreeRootLike[],
): TreeRootLike | undefined {
  if (orb.categoryId != null && byId.has(orb.categoryId)) {
    return byId.get(orb.categoryId);
  }
  const byExact = l1.find((r) => namesLooselyMatch(r.name, orb.name));
  if (byExact) return byExact;
  if (orb.slugHint) {
    const slugN = normalizeFa(orb.slugHint);
    return l1.find((r) => r.slug && normalizeFa(r.slug).includes(slugN));
  }
  return undefined;
}

function orbFromRoot(
  root: TreeRootLike,
  previous: HeroCategoryDock,
): HeroOrbCategory {
  const prevByName = new Map(previous.categories.map((c) => [normalizeFa(c.name), c]));
  const prevById = new Map(
    previous.categories
      .filter((c) => c.categoryId != null)
      .map((c) => [c.categoryId!, c]),
  );
  const marketingByName = new Map(
    DEFAULT_CATEGORY_DOCK.categories.map((c) => [normalizeFa(c.name), c]),
  );
  const marketing = marketingByName.get(normalizeFa(root.name));
  const prev =
    (root.id != null ? prevById.get(root.id) : undefined) ??
    (marketing
      ? previous.categories.find((c) => c.key === marketing.key)
      : undefined) ??
    prevByName.get(normalizeFa(root.name)) ??
    marketing;

  return {
    key: marketing?.key ?? root.slug ?? `cat-${root.id}`,
    name: root.name,
    icon:
      (root.icon && root.icon.trim()) ||
      prev?.icon ||
      marketing?.icon ||
      "Category",
    productCount: root.product_count ?? prev?.productCount ?? 0,
    heroImage: prev?.heroImage || marketing?.heroImage || "/images/hero/hero-cutting-left.jpg",
    subtitle:
      prev?.subtitle ||
      marketing?.subtitle ||
      `محصولات دسته «${root.name}» در فروشگاه کارزار`,
    ctaLabel: prev?.ctaLabel || marketing?.ctaLabel || "ورود",
    featuredOrder:
      prev?.featuredOrder !== undefined
        ? prev.featuredOrder
        : (marketing?.featuredOrder ?? null),
    slugHint: root.slug ?? marketing?.slugHint ?? "",
    categoryId: root.id,
  };
}

/**
 * Full rebuild: every L1 root becomes a dock member (used when dock is empty / first sync).
 * Always prepends the special discounts orb.
 */
export function categoryDockFromRoots(
  roots: TreeRootLike[],
  previous: HeroCategoryDock = DEFAULT_CATEGORY_DOCK,
): HeroCategoryDock {
  const l1 = roots.filter((r) => r.parent_id == null);
  if (!l1.length) return previous;
  const prevDiscount = previous.categories.find((c) => isSpecialDockOrb(c));
  return {
    categories: [createDiscountsOrb(prevDiscount), ...l1.map((root) => orbFromRoot(root, previous))],
  };
}

export interface DockSyncResult {
  dock: HeroCategoryDock;
  /** L1 roots not currently in the dock — available to add */
  available: TreeRootLike[];
  added: number;
  updated: number;
  removed: number;
}

function ensureDiscountsOrb(categories: HeroOrbCategory[]): HeroOrbCategory[] {
  const idx = categories.findIndex((c) => isSpecialDockOrb(c));
  if (idx >= 0) {
    const prev = categories[idx]!;
    const next = {
      ...createDiscountsOrb(prev),
      featuredOrder: prev.featuredOrder,
      heroImage: prev.heroImage || createDiscountsOrb().heroImage,
      subtitle: prev.subtitle || createDiscountsOrb().subtitle,
      ctaLabel: prev.ctaLabel || createDiscountsOrb().ctaLabel,
      icon: prev.icon || createDiscountsOrb().icon,
      name: prev.name || "تخفیف‌ها",
      special: true as const,
      key: DISCOUNTS_ORB_KEY,
    };
    return categories.map((c, i) => (i === idx ? next : c));
  }
  return [createDiscountsOrb(), ...categories];
}

/**
 * Smart sync: refresh dock members from live L1, drop deleted cats, keep order/featured.
 * Optionally append new L1 roots that are not yet in the dock (`appendNew`).
 * Special discounts orb is never wiped even without an L1 match.
 */
export function syncDockWithRoots(
  roots: TreeRootLike[],
  previous: HeroCategoryDock = DEFAULT_CATEGORY_DOCK,
  options: { appendNew?: boolean } = { appendNew: false },
): DockSyncResult {
  const l1 = roots.filter((r) => r.parent_id == null);
  if (!l1.length) {
    return { dock: previous, available: [], added: 0, updated: 0, removed: 0 };
  }

  // Seed empty dock from all L1 once.
  if (!previous.categories.length) {
    const seeded = categoryDockFromRoots(l1, previous);
    return {
      dock: seeded,
      available: [],
      added: seeded.categories.length,
      updated: 0,
      removed: 0,
    };
  }

  const byId = new Map(l1.map((r) => [r.id, r]));
  let updated = 0;
  let removed = 0;

  const kept: HeroOrbCategory[] = [];
  for (const orb of previous.categories) {
    if (isSpecialDockOrb(orb)) {
      kept.push({
        ...createDiscountsOrb(orb),
        featuredOrder: orb.featuredOrder,
        heroImage: orb.heroImage || createDiscountsOrb().heroImage,
        subtitle: orb.subtitle || createDiscountsOrb().subtitle,
        ctaLabel: orb.ctaLabel || createDiscountsOrb().ctaLabel,
        icon: orb.icon || createDiscountsOrb().icon,
        name: orb.name || "تخفیف‌ها",
      });
      continue;
    }
    const root = findRootForOrb(orb, byId, l1);
    if (!root) {
      removed += 1;
      continue;
    }
    const next = orbFromRoot(root, { categories: [orb] });
    // Preserve featured + dock identity from previous orb
    kept.push({
      ...next,
      key: orb.key,
      featuredOrder: orb.featuredOrder,
      heroImage: orb.heroImage || next.heroImage,
      subtitle: orb.subtitle || next.subtitle,
      ctaLabel: orb.ctaLabel || next.ctaLabel,
      icon: orb.icon || next.icon,
    });
    if (
      next.name !== orb.name ||
      next.productCount !== orb.productCount ||
      next.categoryId !== orb.categoryId
    ) {
      updated += 1;
    }
  }

  // If every curated row failed to match (rename wave), remap from L1 instead of wiping.
  if (!kept.length && previous.categories.length && l1.length) {
    const remapped = categoryDockFromRoots(l1, previous);
    return {
      dock: remapped,
      available: [],
      added: remapped.categories.length,
      updated: 0,
      removed: previous.categories.length,
    };
  }

  const dockIds = new Set(kept.map((c) => c.categoryId).filter((id): id is number => id != null));
  const dockNames = new Set(kept.map((c) => normalizeFa(c.name)));

  const available = l1.filter(
    (r) =>
      !dockIds.has(r.id) &&
      !dockNames.has(normalizeFa(r.name)) &&
      !kept.some((c) => namesLooselyMatch(c.name, r.name)),
  );

  let added = 0;
  let categories = ensureDiscountsOrb(kept);
  if (options.appendNew && available.length) {
    const extras = available.map((root) => {
      const orb = orbFromRoot(root, previous);
      return { ...orb, featuredOrder: null as number | null };
    });
    categories = [...categories, ...extras];
    added = extras.length;
  }

  // Preserve sparse featured slots 0–4 (do not collapse gaps).
  const maxSlot = HERO_FEATURED_SLOT_COUNT - 1;
  const claimed = new Map<number, string>();
  categories = categories.map((c) => {
    if (c.featuredOrder == null) return { ...c, featuredOrder: null };
    const slot = Math.max(0, Math.min(maxSlot, Math.floor(c.featuredOrder)));
    if (claimed.has(slot)) return { ...c, featuredOrder: null };
    claimed.set(slot, c.key);
    return { ...c, featuredOrder: slot };
  });

  return {
    dock: { categories },
    available: options.appendNew ? [] : available,
    added,
    updated,
    removed,
  };
}

/** Build a dock orb from an L1 tree node for manual add. */
export function orbFromTreeRoot(
  root: TreeRootLike,
  previous: HeroCategoryDock = DEFAULT_CATEGORY_DOCK,
): HeroOrbCategory {
  return { ...orbFromRoot(root, previous), featuredOrder: null };
}

export function configFromOrb(orb: HeroOrbCategory): HeroBuilderConfig {
  const base = createDefaultConfig();
  const primaryHref = isSpecialDockOrb(orb)
    ? DISCOUNTS_CATALOG_HREF
    : `/catalog?q=${encodeURIComponent(orb.name)}`;
  return {
    ...base,
    linkedOrbKey: orb.key,
    minHeight: 720,
    background: {
      ...base.background,
      mode: "image",
      imageUrl: orb.heroImage,
      focal: "left 42%",
    },
    overlay: {
      ...base.overlay,
      gradientFrom: "rgba(12,12,12,0.08)",
      gradientTo: "rgba(12,12,12,0.86)",
      gradientAngle: 90,
    },
    typography: {
      ...base.typography,
      title: orb.name,
      subtitle: orb.subtitle,
      position: { x: 5, y: 26 },
      maxWidth: 460,
    },
    buttons: [
      {
        id: createId("btn"),
        label: orb.ctaLabel,
        variant: "solid",
        bgColor: "#D02327",
        textColor: "#FFFFFF",
        borderRadius: 12,
        position: { x: 5, y: 58 },
        action: {
          type: "href",
          value: primaryHref,
        },
        stylePreset: "primary",
        sizePreset: "lg",
      },
      {
        id: createId("btn"),
        label: "کاتالوگ",
        variant: "glass",
        bgColor: "rgba(255,255,255,0.12)",
        textColor: "#FFFFFF",
        borderRadius: 12,
        position: { x: 5, y: 70 },
        action: { type: "href", value: "/catalog" },
        stylePreset: "on-dark-glass",
        sizePreset: "md",
      },
    ],
    badges: isSpecialDockOrb(orb)
      ? [
          {
            id: createId("badge"),
            kind: "discount",
            style: "pill",
            label: "تخفیف ویژه",
            meta: "پرتخفیف",
            position: { x: 5, y: 14 },
            animated: true,
          },
        ]
      : [],
  };
}

export function createDefaultConfig(): HeroBuilderConfig {
  return {
    version: 1,
    minHeight: 720,
    animation: "fade-up",
    linkedOrbKey: null,
    background: {
      mode: "image",
      imageUrl: "/images/hero/hero-metrology-left.jpg",
      color: "#121212",
      focal: "left 42%",
    },
    overlay: {
      mode: "gradient",
      solidColor: "rgba(12,12,12,0.72)",
      gradientFrom: "rgba(12,12,12,0.08)",
      gradientTo: "rgba(12,12,12,0.86)",
      gradientAngle: 90,
      opacity: 1,
    },
    typography: {
      title: "اندازه‌گیری دقیق",
      subtitle:
        "کولیس، میکرومتر و گیج‌های صنعتی — کنترل کیفیت مطمئن برای خط تولید شما",
      titleColor: "#FFFFFF",
      subtitleColor: "rgba(255,255,255,0.9)",
      titleSize: 42,
      subtitleSize: 16,
      align: "start",
      position: { x: 5, y: 26 },
      maxWidth: 460,
    },
    buttons: [
      {
        id: createId("btn"),
        label: "مشاهده اندازه‌گیری",
        variant: "solid",
        bgColor: "#D02327",
        textColor: "#FFFFFF",
        borderRadius: 12,
        position: { x: 5, y: 58 },
        action: { type: "href", value: "/catalog" },
        stylePreset: "primary",
        sizePreset: "lg",
      },
      {
        id: createId("btn"),
        label: "استعلام قیمت",
        variant: "glass",
        bgColor: "rgba(255,255,255,0.12)",
        textColor: "#FFFFFF",
        borderRadius: 12,
        position: { x: 5, y: 70 },
        action: { type: "href", value: "/quote" },
        stylePreset: "on-dark-glass",
        sizePreset: "md",
      },
    ],
    badges: [],
    carousel: {
      enabled: false,
      categorySlug: "",
      categoryLabel: "پرفروش‌ها",
      position: { x: 52, y: 56 },
      maxItems: 4,
      previewTitles: [],
      stylePreset: "rail-soft",
      layoutPreset: "row-comfortable",
      productIds: [],
      categoryId: null,
    },
  };
}

export function createSlide(partial?: Partial<HeroSlideDraft>): HeroSlideDraft {
  return {
    id: partial?.id ?? createId("slide"),
    name: partial?.name ?? "اسلاید جدید",
    sortOrder: partial?.sortOrder ?? 1,
    isActive: partial?.isActive ?? true,
    isPlaceholder: partial?.isPlaceholder ?? false,
    cmsId: partial?.cmsId,
    mobilePreset: partial?.mobilePreset,
    config: partial?.config ?? createDefaultConfig(),
  };
}

export function createDefaultProject(): HeroDesignProject {
  const dock = structuredClone(DEFAULT_CATEGORY_DOCK);
  const slides = curatedSlidesFromDock(dock.categories);
  return normalizeHeroProject({
    version: 1,
    activeSlideId: slides[0]!.id,
    slides,
    categoryDock: dock,
    showGrid: false,
    snapToGrid: true,
    gridSize: 4,
    previewDevice: "desktop",
    mobilePreset: "balanced",
  });
}

export const DEFAULT_HERO_CONFIG = createDefaultConfig();
