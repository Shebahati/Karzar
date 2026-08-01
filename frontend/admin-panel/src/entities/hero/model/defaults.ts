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

export const DEFAULT_CATEGORY_DOCK: HeroCategoryDock = {
  categories: [
    {
      key: "metrology",
      name: "اندازه‌گیری",
      icon: "/category-icons/andaze-giri.png",
      productCount: 0,
      heroImage: "/images/hero/hero-metrology-left.jpg",
      subtitle:
        "کولیس، میکرومتر و گیج‌های صنعتی — دقت قابل‌اعتماد برای کنترل کیفیت خط تولید",
      ctaLabel: "ورود",
      featuredOrder: 0,
      slugHint: "andaze-giri",
    },
    {
      key: "insert-tools",
      name: "ابزار اینسرتی",
      icon: "/category-icons/abzar-inserti.png",
      productCount: 0,
      heroImage: "/images/hero/hero-cutting-left.jpg",
      subtitle: "هلدر و سیستم‌های اینسرتی برای براده‌برداری پایدار و تعویض سریع",
      ctaLabel: "ورود",
      featuredOrder: 1,
      slugHint: "abzar-inserti",
    },
    {
      key: "inserts",
      name: "اینسرت",
      icon: "/category-icons/insert.png",
      productCount: 0,
      heroImage: "/images/hero/hero-cutting-left.jpg",
      subtitle: "اینسرت‌های کاربیدی و پوشش‌دار برای سطوح برش متنوع",
      ctaLabel: "ورود",
      featuredOrder: 2,
      slugHint: "insert",
    },
    {
      key: "endmills",
      name: "فرز انگشتی",
      icon: "/category-icons/farz-angoshti.png",
      productCount: 0,
      heroImage: "/images/hero/hero-cutting-left.jpg",
      subtitle: "فرز انگشتی و ابزارهای پروفایل برای ماشین‌کاری دقیق قطعه",
      ctaLabel: "ورود",
      featuredOrder: 3,
      slugHint: "farz-angoshti",
    },
    {
      key: "taps",
      name: "قلاویز",
      icon: "/category-icons/ghalaviz.png",
      productCount: 0,
      heroImage: "/images/hero/hero-cutting-left.jpg",
      subtitle: "قلاویز دستی و ماشینی برای رزوه‌کاری استاندارد صنعتی",
      ctaLabel: "ورود",
      featuredOrder: null,
      slugHint: "ghalaviz",
    },
    {
      key: "toolholders",
      name: "ابزار گیر",
      icon: "/category-icons/abzar-gir.png",
      productCount: 0,
      heroImage: "/images/hero/hero-holding-left.jpg",
      subtitle: "هولدر و رابط‌های ابزار برای پایداری بیشتر در اسپیندل",
      ctaLabel: "ورود",
      featuredOrder: null,
      slugHint: "abzar-gir",
    },
    {
      key: "workholding",
      name: "ابزار گیرشی",
      icon: "/category-icons/abzar-gireshi.png",
      productCount: 0,
      heroImage: "/images/hero/hero-holding-left.jpg",
      subtitle: "گیره‌ها و سیستم‌های فیکسچر برای نگهداشت ایمن قطعه کار",
      ctaLabel: "ورود",
      featuredOrder: 4,
      slugHint: "abzar-gireshi",
    },
    {
      key: "industrial-machines",
      name: "دستگاه‌های صنعتی",
      icon: "/category-icons/dastgah-sanati.png",
      productCount: 0,
      heroImage: "/images/hero/hero-machines-left.jpg",
      subtitle: "ماشین‌ها و تجهیزات صنعتی برای تجهیز کارگاه و خط تولید",
      ctaLabel: "ورود",
      featuredOrder: 5,
      slugHint: "dastgah-sanati",
    },
    {
      key: "heli-coil",
      name: "هلی کویل",
      icon: "/category-icons/heli-coil.png",
      productCount: 0,
      heroImage: "/images/hero/hero-cutting-left.jpg",
      subtitle: "فنر، قلاویز و کیت‌های هلی‌کویل برای ترمیم رزوه",
      ctaLabel: "ورود",
      featuredOrder: null,
      slugHint: "heli-coil",
    },
    {
      key: "drills",
      name: "مته",
      icon: "/category-icons/mete.png",
      productCount: 0,
      heroImage: "/images/hero/hero-cutting-left.jpg",
      subtitle: "مته‌های HSS و کاربید برای سوراخ‌کاری تمیز و تکرارپذیر",
      ctaLabel: "ورود",
      featuredOrder: null,
      slugHint: "mete",
    },
    {
      key: "workshop-tools",
      name: "ابزار کارگاهی : دریل عادی",
      icon: "/category-icons/abzar-kargahi.png",
      productCount: 0,
      heroImage: "/images/hero/hero-holding-left.jpg",
      subtitle: "ابزار کارگاهی و دریل عادی برای کار روزمره کارگاه",
      ctaLabel: "ورود",
      featuredOrder: null,
      slugHint: "abzar-kargahi",
    },
    {
      key: "lubricants",
      name: "روغن و روانکار",
      icon: "/category-icons/roghan-ravankar.png",
      productCount: 0,
      heroImage: "/images/hero/hero-accessories-left.jpg",
      subtitle: "روغن برش و روانکار صنعتی برای طول عمر ابزار و کیفیت سطح",
      ctaLabel: "ورود",
      featuredOrder: null,
      slugHint: "roghan-ravankar",
    },
  ],
};

export function featuredDockCategories(
  dock: HeroCategoryDock = DEFAULT_CATEGORY_DOCK,
): HeroOrbCategory[] {
  return [...dock.categories]
    .filter((c) => c.featuredOrder != null)
    .sort((a, b) => (a.featuredOrder ?? 0) - (b.featuredOrder ?? 0))
    .slice(0, 6);
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
 */
export function categoryDockFromRoots(
  roots: TreeRootLike[],
  previous: HeroCategoryDock = DEFAULT_CATEGORY_DOCK,
): HeroCategoryDock {
  const l1 = roots.filter((r) => r.parent_id == null);
  if (!l1.length) return previous;
  return { categories: l1.map((root) => orbFromRoot(root, previous)) };
}

export interface DockSyncResult {
  dock: HeroCategoryDock;
  /** L1 roots not currently in the dock — available to add */
  available: TreeRootLike[];
  added: number;
  updated: number;
  removed: number;
}

/**
 * Smart sync: refresh dock members from live L1, drop deleted cats, keep order/featured.
 * Optionally append new L1 roots that are not yet in the dock (`appendNew`).
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
  let categories = kept;
  if (options.appendNew && available.length) {
    const extras = available.map((root) => {
      const orb = orbFromRoot(root, previous);
      return { ...orb, featuredOrder: null as number | null };
    });
    categories = [...kept, ...extras];
    added = extras.length;
  }

  // Preserve sparse featured slots 0–5 (do not collapse gaps).
  const claimed = new Map<number, string>();
  categories = categories.map((c) => {
    if (c.featuredOrder == null) return { ...c, featuredOrder: null };
    const slot = Math.max(0, Math.min(5, Math.floor(c.featuredOrder)));
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
          value: `/catalog?q=${encodeURIComponent(orb.name)}`,
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
    badges: [],
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
    id: createId("slide"),
    name: partial?.name ?? "اسلاید جدید",
    sortOrder: partial?.sortOrder ?? 1,
    isActive: partial?.isActive ?? true,
    cmsId: partial?.cmsId,
    mobilePreset: partial?.mobilePreset,
    config: partial?.config ?? createDefaultConfig(),
  };
}

export function createDefaultProject(): HeroDesignProject {
  const dock = structuredClone(DEFAULT_CATEGORY_DOCK);
  const slides = curatedSlidesFromDock(dock.categories);
  return {
    version: 1,
    activeSlideId: slides[0]!.id,
    slides,
    categoryDock: dock,
    showGrid: false,
    snapToGrid: true,
    gridSize: 4,
    previewDevice: "desktop",
    mobilePreset: "balanced",
  };
}

export const DEFAULT_HERO_CONFIG = createDefaultConfig();
