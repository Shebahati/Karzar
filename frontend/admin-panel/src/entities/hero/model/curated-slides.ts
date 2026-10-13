/**
 * Curated hero seeds — approved five-hero Reborn campaign (photo + type + CTA).
 * Order matches featured dock keys; no extra filler slides.
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
  mobileImage: string;
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
  ctaSecondary?: CtaSeed;
};

const REBORN_HERO = "/images/hero/reborn-5";

/** Approved Reborn-5 campaign seeds (order = featured dock). */
export const CURATED_HERO_SEEDS: SlideSeed[] = [
  {
    orbKey: DISCOUNTS_ORB_KEY,
    name: "تخفیف‌ها",
    title: "تخفیف‌های ویژه‌ی کارزار",
    subtitle: "پیشنهادهای ویژه برای خرید به‌صرفه‌تر ابزار و تجهیزات صنعتی.",
    image: `${REBORN_HERO}/H01-special-offers-native-lossless.webp`,
    mobileImage: `${REBORN_HERO}/H01-special-offers-1280.webp`,
    focal: "left 38%",
    animation: "fade-up",
    minHeight: 760,
    mobilePreset: "balanced",
    overlay: {
      gradientFrom: "rgba(8,8,8,0.12)",
      gradientTo: "rgba(8,8,8,0.58)",
      gradientAngle: 105,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 460,
      titleSize: 44,
      subtitleSize: 17,
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
    title: "ابزار اندازه‌گیری",
    subtitle: "مجموعه‌ای متنوع از ابزارهای اندازه‌گیری برای سنجش دقیق و کنترل کیفیت.",
    image: `${REBORN_HERO}/H02-measuring-tools-native-lossless.webp`,
    mobileImage: `${REBORN_HERO}/H02-measuring-tools-1280.webp`,
    focal: "left 40%",
    animation: "fade-up",
    minHeight: 760,
    mobilePreset: "balanced",
    overlay: {
      gradientFrom: "rgba(8,8,8,0.12)",
      gradientTo: "rgba(8,8,8,0.58)",
      gradientAngle: 105,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 460,
      titleSize: 44,
      subtitleSize: 17,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده ابزار اندازه‌گیری",
      href: "/categories/andaze-giri",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 58 },
    },
  },
  {
    orbKey: "inserts",
    name: "اینسرت و ابزارهای اینسرتی",
    title: "اینسرت و ابزارهای اینسرتی",
    subtitle: "انتخاب ابزار متناسب با جنس قطعه، نوع عملیات و شرایط ماشین‌کاری.",
    image: `${REBORN_HERO}/H03-inserts-turning-tools-native-lossless.webp`,
    mobileImage: `${REBORN_HERO}/H03-inserts-turning-tools-1280.webp`,
    focal: "left 42%",
    animation: "fade-up",
    minHeight: 760,
    mobilePreset: "balanced",
    overlay: {
      gradientFrom: "rgba(8,8,8,0.12)",
      gradientTo: "rgba(8,8,8,0.58)",
      gradientAngle: 105,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 460,
      titleSize: 44,
      subtitleSize: 17,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده اینسرت‌ها",
      href: "/categories/insert",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 58 },
    },
    ctaSecondary: {
      label: "مشاهده ابزارهای اینسرتی",
      href: "/categories/abzar-inserti",
      stylePreset: "soft",
      sizePreset: "lg",
      position: { x: 6, y: 68 },
    },
  },
  {
    orbKey: "endmills",
    name: "فرز انگشتی",
    title: "فرز انگشتی",
    subtitle: "هندسه‌ها و ابعاد متنوع برای ماشین‌کاری قطعات و سطوح مختلف.",
    image: `${REBORN_HERO}/H04-end-mills-native-lossless.webp`,
    mobileImage: `${REBORN_HERO}/H04-end-mills-1280.webp`,
    focal: "left 44%",
    animation: "fade-up",
    minHeight: 760,
    mobilePreset: "balanced",
    overlay: {
      gradientFrom: "rgba(8,8,8,0.12)",
      gradientTo: "rgba(8,8,8,0.58)",
      gradientAngle: 105,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 460,
      titleSize: 44,
      subtitleSize: 17,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده فرزهای انگشتی",
      href: "/categories/farz-angoshti",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 58 },
    },
  },
  {
    orbKey: "industrial-machines",
    name: "دستگاه‌های صنعتی",
    title: "دستگاه‌های صنعتی",
    subtitle: "تجهیز کارگاه و خط تولید با دستگاه‌های متناسب با نیازهای صنعتی شما.",
    image: `${REBORN_HERO}/H05-industrial-machines-native-lossless.webp`,
    mobileImage: `${REBORN_HERO}/H05-industrial-machines-1280.webp`,
    focal: "left 36%",
    animation: "fade-up",
    minHeight: 760,
    mobilePreset: "balanced",
    overlay: {
      gradientFrom: "rgba(8,8,8,0.12)",
      gradientTo: "rgba(8,8,8,0.58)",
      gradientAngle: 105,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 460,
      titleSize: 44,
      subtitleSize: 17,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده دستگاه‌های صنعتی",
      href: "/categories/dastgah-sanati",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 58 },
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
      mobileImageUrl: seed.mobileImage,
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
    buttons: [
      buttonFromCta(seed.ctaPrimary),
      ...(seed.ctaSecondary ? [buttonFromCta(seed.ctaSecondary)] : []),
    ],
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
 * Build the fixed five-slide pack from featured dock keys (campaign order).
 */
export function curatedSlidesFromDock(orbs: HeroOrbCategory[]): HeroSlideDraft[] {
  const SLIDE_SLOTS = 5; // keep in sync with HERO_SLIDE_SLOT_COUNT in defaults
  const featured = [...orbs]
    .filter((c) => c.featuredOrder != null)
    .sort((a, b) => (a.featuredOrder ?? 0) - (b.featuredOrder ?? 0))
    .slice(0, SLIDE_SLOTS);

  const seeds: SlideSeed[] = [];
  for (const orb of featured) {
    const seed = CURATED_HERO_SEEDS.find((s) => s.orbKey === orb.key);
    if (seed) seeds.push(seed);
  }

  return seeds.slice(0, SLIDE_SLOTS).map((seed, i) => {
    const orb = orbs.find((o) => o.key === seed.orbKey);
    const config = configFromCuratedSeed(seed);
    if (orb) {
      config.background.imageUrl = seed.image;
      config.background.mobileImageUrl = seed.mobileImage;
      config.typography.title = seed.title;
      config.typography.subtitle = seed.subtitle;
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
