/**
 * Curated hero seeds — clean industrial slides (photo + type + one CTA).
 * No badges / fake product carousels. Pack uses 6: featured dock (5) + filler.
 */

import type {
  DsButtonSize,
  DsButtonStyle,
  HeroAnimationPreset,
  HeroBuilderConfig,
  HeroOrbCategory,
  HeroSlideDraft,
  MobileComposePreset,
  TextAlign,
} from "./types";
import { DISCOUNTS_CATALOG_HREF, DISCOUNTS_ORB_KEY } from "@/config/l1-categories";
import { buttonStyleCss } from "./presets";

function createId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 9)}`;
}

type CtaSeed = {
  label: string;
  href: string;
  stylePreset: DsButtonStyle;
  sizePreset: DsButtonSize;
  position: { x: number; y: number };
};

type SlideSeed = {
  orbKey: string;
  name: string;
  title: string;
  subtitle: string;
  image: string;
  focal: string;
  animation: HeroAnimationPreset;
  minHeight: number;
  mobilePreset: MobileComposePreset;
  overlay: {
    gradientFrom: string;
    gradientTo: string;
    gradientAngle: number;
    opacity?: number;
  };
  typography: {
    position: { x: number; y: number };
    maxWidth: number;
    titleSize: number;
    subtitleSize: number;
    align: TextAlign;
  };
  ctaPrimary: CtaSeed;
};

/** Clean seeds — composition / temperature vary; chrome stays minimal. */
export const CURATED_HERO_SEEDS: SlideSeed[] = [
  {
    orbKey: DISCOUNTS_ORB_KEY,
    name: "تخفیف‌ها",
    title: "تخفیف‌های ویژه کارزار",
    subtitle: "ابزار صنعتی منتخب با قیمت رقابتی برای تجهیز کارگاه و خط تولید",
    image: "/images/hero/hero-accessories-left.jpg",
    focal: "left 40%",
    animation: "fade-up",
    minHeight: 760,
    mobilePreset: "copy-focus",
    overlay: {
      gradientFrom: "rgba(28,10,10,0.2)",
      gradientTo: "rgba(8,6,6,0.88)",
      gradientAngle: 105,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 420,
      titleSize: 46,
      subtitleSize: 16,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده تخفیف‌ها",
      href: DISCOUNTS_CATALOG_HREF,
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 58 },
    },
  },
  {
    orbKey: "metrology",
    name: "اندازه‌گیری",
    title: "اندازه‌گیری دقیق",
    subtitle: "کولیس، میکرومتر و گیج‌های صنعتی از برندهای معتبر",
    image: "/images/hero/hero-metrology-left.jpg",
    focal: "center left",
    animation: "fade-in",
    minHeight: 720,
    mobilePreset: "balanced",
    overlay: {
      gradientFrom: "rgba(10,12,16,0.1)",
      gradientTo: "rgba(8,10,12,0.86)",
      gradientAngle: 255,
    },
    typography: {
      position: { x: 48, y: 30 },
      maxWidth: 400,
      titleSize: 44,
      subtitleSize: 16,
      align: "end",
    },
    ctaPrimary: {
      label: "مشاهده اندازه‌گیری",
      href: "/categories/andaze-giri",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 62, y: 58 },
    },
  },
  {
    orbKey: "insert-tools",
    name: "ابزار اینسرتی",
    title: "ابزار اینسرتی",
    subtitle: "هلدر و سیستم‌های اینسرتی برای براده‌برداری پایدار و تعویض سریع",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "right 42%",
    animation: "fade-in",
    minHeight: 710,
    mobilePreset: "copy-focus",
    overlay: {
      gradientFrom: "rgba(40,40,40,0.22)",
      gradientTo: "rgba(12,12,12,0.86)",
      gradientAngle: 70,
    },
    typography: {
      position: { x: 50, y: 30 },
      maxWidth: 380,
      titleSize: 42,
      subtitleSize: 16,
      align: "end",
    },
    ctaPrimary: {
      label: "مشاهده ابزار اینسرتی",
      href: "/categories/abzar-inserti",
      stylePreset: "soft",
      sizePreset: "lg",
      position: { x: 58, y: 58 },
    },
  },
  {
    orbKey: "inserts",
    name: "اینسرت",
    title: "اینسرت کاربیدی",
    subtitle: "پوشش‌های صنعتی برای سطوح برش متنوع — عمر طولانی، کیفیت ثابت",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "center",
    animation: "zoom-soft",
    minHeight: 700,
    mobilePreset: "media-focus",
    overlay: {
      gradientFrom: "rgba(12,12,12,0.45)",
      gradientTo: "rgba(12,12,12,0.78)",
      gradientAngle: 180,
    },
    typography: {
      position: { x: 24, y: 32 },
      maxWidth: 440,
      titleSize: 44,
      subtitleSize: 16,
      align: "center",
    },
    ctaPrimary: {
      label: "مشاهده اینسرت",
      href: "/categories/insert",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 38, y: 58 },
    },
  },
  {
    orbKey: "endmills",
    name: "فرز انگشتی",
    title: "فرز انگشتی دقیق",
    subtitle: "ابزار پروفایل و فرز انگشتی برای ماشین‌کاری تمیز",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "left 44%",
    animation: "fade-up",
    minHeight: 720,
    mobilePreset: "balanced",
    overlay: {
      gradientFrom: "rgba(12,12,12,0.15)",
      gradientTo: "rgba(12,12,12,0.88)",
      gradientAngle: 92,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 420,
      titleSize: 42,
      subtitleSize: 16,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده فرز انگشتی",
      href: "/categories/farz-angoshti",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 56 },
    },
  },
  {
    orbKey: "taps",
    name: "قلاویز",
    title: "قلاویز صنعتی",
    subtitle: "قلاویز دستی و ماشینی برای رزوه‌کاری استاندارد",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "left 36%",
    animation: "fade-in",
    minHeight: 690,
    mobilePreset: "dock-first",
    overlay: {
      gradientFrom: "rgba(12,16,22,0.18)",
      gradientTo: "rgba(12,12,12,0.86)",
      gradientAngle: 110,
    },
    typography: {
      position: { x: 8, y: 30 },
      maxWidth: 360,
      titleSize: 40,
      subtitleSize: 15,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده قلاویز",
      href: "/categories/ghalaviz",
      stylePreset: "soft",
      sizePreset: "lg",
      position: { x: 8, y: 56 },
    },
  },
  {
    orbKey: "toolholders",
    name: "ابزار گیر",
    title: "ابزارگیر دقیق",
    subtitle: "هولدر و رابط‌های ابزار برای پایداری بیشتر در اسپیندل",
    image: "/images/hero/hero-holding-left.jpg",
    focal: "left 50%",
    animation: "fade-up",
    minHeight: 730,
    mobilePreset: "media-focus",
    overlay: {
      gradientFrom: "rgba(12,12,12,0.2)",
      gradientTo: "rgba(12,12,12,0.84)",
      gradientAngle: 88,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 400,
      titleSize: 42,
      subtitleSize: 16,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده ابزار گیر",
      href: "/categories/abzar-gir",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 56 },
    },
  },
  {
    orbKey: "workholding",
    name: "ابزار گیرشی",
    title: "ثابت‌کاری حرفه‌ای",
    subtitle: "گیره، فیکسچر و سیستم‌های نگه‌دارنده برای ماشین‌کاری پایدار",
    image: "/images/hero/hero-holding-left.jpg",
    focal: "left 46%",
    animation: "slide-in",
    minHeight: 740,
    mobilePreset: "dock-first",
    overlay: {
      gradientFrom: "rgba(12,16,20,0.12)",
      gradientTo: "rgba(6,8,10,0.9)",
      gradientAngle: 95,
    },
    typography: {
      position: { x: 6, y: 26 },
      maxWidth: 400,
      titleSize: 44,
      subtitleSize: 16,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده ابزار گیرشی",
      href: "/categories/abzar-gireshi",
      stylePreset: "on-dark-outline",
      sizePreset: "lg",
      position: { x: 6, y: 56 },
    },
  },
  {
    orbKey: "industrial-machines",
    name: "دستگاه‌های صنعتی",
    title: "ظرفیت کارگاه را بالا ببرید",
    subtitle: "ماشین‌ها و تجهیزات صنعتی با انتخاب تخصصی و پشتیبانی کارزار",
    image: "/images/hero/hero-machines-left.jpg",
    focal: "left 34%",
    animation: "fade-up",
    minHeight: 780,
    mobilePreset: "media-focus",
    overlay: {
      gradientFrom: "rgba(8,10,14,0.18)",
      gradientTo: "rgba(4,5,8,0.92)",
      gradientAngle: 112,
    },
    typography: {
      position: { x: 6, y: 24 },
      maxWidth: 460,
      titleSize: 48,
      subtitleSize: 16,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده دستگاه‌ها",
      href: "/categories/dastgah-sanati",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 56 },
    },
  },
  {
    orbKey: "heli-coil",
    name: "هلی کویل",
    title: "ترمیم رزوه هلی‌کویل",
    subtitle: "فنر، قلاویز و کیت‌های هلی‌کویل برای ترمیم رزوه",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "right 42%",
    animation: "fade-in",
    minHeight: 700,
    mobilePreset: "copy-focus",
    overlay: {
      gradientFrom: "rgba(20,14,12,0.18)",
      gradientTo: "rgba(12,12,12,0.86)",
      gradientAngle: 100,
    },
    typography: {
      position: { x: 6, y: 30 },
      maxWidth: 380,
      titleSize: 40,
      subtitleSize: 15,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده هلی کویل",
      href: "/categories/heli-coil",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 56 },
    },
  },
  {
    orbKey: "drills",
    name: "مته",
    title: "مته‌های صنعتی",
    subtitle: "مته‌های HSS و کاربید برای سوراخ‌کاری تمیز و تکرارپذیر",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "left 46%",
    animation: "zoom-soft",
    minHeight: 720,
    mobilePreset: "balanced",
    overlay: {
      gradientFrom: "rgba(12,12,12,0.14)",
      gradientTo: "rgba(12,12,12,0.88)",
      gradientAngle: 90,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 400,
      titleSize: 42,
      subtitleSize: 16,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده مته",
      href: "/categories/mete",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 56 },
    },
  },
  {
    orbKey: "workshop-tools",
    name: "ابزار کارگاهی : دریل عادی",
    title: "ابزار کارگاهی",
    subtitle: "ابزار کارگاهی و دریل عادی برای کار روزمره کارگاه",
    image: "/images/hero/hero-holding-left.jpg",
    focal: "left 55%",
    animation: "fade-in",
    minHeight: 700,
    mobilePreset: "dock-first",
    overlay: {
      gradientFrom: "rgba(12,12,12,0.22)",
      gradientTo: "rgba(12,12,12,0.84)",
      gradientAngle: 85,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 380,
      titleSize: 40,
      subtitleSize: 15,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده ابزار کارگاهی",
      href: "/categories/abzar-kargahi",
      stylePreset: "soft",
      sizePreset: "lg",
      position: { x: 6, y: 56 },
    },
  },
  {
    orbKey: "lubricants",
    name: "روغن و روانکار",
    title: "روغن و روانکار",
    subtitle: "روغن برش و روانکار صنعتی برای طول عمر ابزار و کیفیت سطح",
    image: "/images/hero/hero-accessories-left.jpg",
    focal: "left 40%",
    animation: "fade-up",
    minHeight: 720,
    mobilePreset: "copy-focus",
    overlay: {
      gradientFrom: "rgba(14,16,14,0.16)",
      gradientTo: "rgba(10,12,10,0.88)",
      gradientAngle: 96,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 420,
      titleSize: 42,
      subtitleSize: 16,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده روغن و روانکار",
      href: "/categories/roghan-ravankar",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 56 },
    },
  },
];

function buttonFromCta(cta: CtaSeed) {
  const css = buttonStyleCss(cta.stylePreset);
  return {
    id: createId("btn"),
    label: cta.label,
    variant:
      cta.stylePreset === "on-dark-outline"
        ? ("outline" as const)
        : cta.stylePreset === "on-dark-glass"
          ? ("glass" as const)
          : ("solid" as const),
    bgColor: css.background,
    textColor: css.color,
    borderRadius: cta.sizePreset === "pill" ? 999 : 12,
    position: cta.position,
    action: { type: "href" as const, value: cta.href },
    stylePreset: cta.stylePreset,
    sizePreset: cta.sizePreset,
  };
}

/** Build one responsive RTL-safe slide config from a seed. */
export function configFromCuratedSeed(seed: SlideSeed): HeroBuilderConfig {
  return {
    version: 1,
    minHeight: seed.minHeight,
    animation: seed.animation,
    linkedOrbKey: seed.orbKey,
    background: {
      mode: "image",
      imageUrl: seed.image,
      color: "#121212",
      focal: seed.focal,
    },
    overlay: {
      mode: "gradient",
      solidColor: "rgba(12,12,12,0.72)",
      gradientFrom: seed.overlay.gradientFrom,
      gradientTo: seed.overlay.gradientTo,
      gradientAngle: seed.overlay.gradientAngle,
      opacity: seed.overlay.opacity ?? 1,
    },
    typography: {
      title: seed.title,
      subtitle: seed.subtitle,
      titleColor: "#FFFFFF",
      subtitleColor: "rgba(255,255,255,0.88)",
      titleSize: seed.typography.titleSize,
      subtitleSize: seed.typography.subtitleSize,
      align: seed.typography.align,
      position: seed.typography.position,
      maxWidth: seed.typography.maxWidth,
    },
    buttons: [buttonFromCta(seed.ctaPrimary)],
    badges: [],
    carousel: {
      enabled: false,
      categorySlug: "",
      categoryLabel: "",
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

/**
 * Build the fixed 6-slide pack: featured dock orbs first (stable keys),
 * then remaining curated seeds until slot count is filled.
 */
export function curatedSlidesFromDock(orbs: HeroOrbCategory[]): HeroSlideDraft[] {
  const SLIDE_SLOTS = 6; // keep in sync with HERO_SLIDE_SLOT_COUNT in defaults
  const featured = [...orbs]
    .filter((c) => c.featuredOrder != null)
    .sort((a, b) => (a.featuredOrder ?? 0) - (b.featuredOrder ?? 0))
    .slice(0, 5);

  const used = new Set<string>();
  const seeds: SlideSeed[] = [];
  for (const orb of featured) {
    const seed = CURATED_HERO_SEEDS.find((s) => s.orbKey === orb.key);
    if (seed && !used.has(seed.orbKey)) {
      seeds.push(seed);
      used.add(seed.orbKey);
    }
  }
  for (const seed of CURATED_HERO_SEEDS) {
    if (seeds.length >= SLIDE_SLOTS) break;
    if (used.has(seed.orbKey)) continue;
    seeds.push(seed);
    used.add(seed.orbKey);
  }

  return seeds.slice(0, SLIDE_SLOTS).map((seed, i) => {
    const orb = orbs.find((o) => o.key === seed.orbKey);
    const config = configFromCuratedSeed(seed);
    if (orb) {
      config.background.imageUrl = orb.heroImage || seed.image;
      if (seed.orbKey === DISCOUNTS_ORB_KEY) {
        config.typography.title = seed.title;
        config.typography.subtitle = orb.subtitle || seed.subtitle;
      } else {
        config.typography.subtitle = orb.subtitle || seed.subtitle;
      }
    }
    return {
      id: `slide_${seed.orbKey}`,
      name: seed.name,
      sortOrder: i + 1,
      isActive: true,
      isPlaceholder: false,
      mobilePreset: seed.mobilePreset,
      config,
    };
  });
}
