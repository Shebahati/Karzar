/**
 * Approved five-hero storefront campaign (Heroes Reborn 5).
 * Single authority for slide order, dock featured keys, copy, and asset paths.
 */

import { CATEGORY_ICON_BY_SLUG } from "@/config/category-icons";
import {
  DISCOUNTS_CATALOG_HREF,
  DISCOUNTS_ORB_KEY,
  DISCOUNTS_SPECIAL,
  FINAL_L1_CATEGORIES,
} from "@/config/l1-categories";
import type { DesignedHeroPack, DesignedHeroSlide } from "@/types/hero-design";

export const HERO_CAMPAIGN_SLIDE_COUNT = 5;

export type HeroCampaignSlideKey =
  | typeof DISCOUNTS_ORB_KEY
  | "metrology"
  | "inserts"
  | "endmills"
  | "industrial-machines";

export type HeroCampaignSlideDef = {
  id: string;
  linkedOrbKey: HeroCampaignSlideKey;
  sortOrder: number;
  name: string;
  title: string;
  subtitle: string;
  desktopImage: string;
  /** Dedicated 4:3 compact art. Not a resize of the 16:9 desktop photograph. */
  mobileImage: string;
  desktopFocal: string;
  /** Independent compact-band anchor (not a vertical tweak of desktop). */
  mobileFocal: string;
  primaryCta: { label: string; href: string };
  secondaryCta?: { label: string; href: string };
  dockLabel: string;
};

/** Versioned path so browsers and the CDN do not reuse the previous generation. */
export const HERO_CALIBRATED_ASSET_DIR =
  "/images/hero/reborn-5/photo-20261021-v2";

/**
 * Desktop masters are 16:9 with the subject cluster on the left.
 * `left` keeps that cluster in frame when the stage is taller than 16:9.
 * The vertical percentage keeps lower-frame equipment when the stage is wider than 16:9.
 * Compact focals are chosen from the dedicated 4:3 compositions, not from the desktop values.
 */
export const HERO_CAMPAIGN_FIVE_SLIDES: HeroCampaignSlideDef[] = [
  {
    id: "slide_h01_special_offers",
    linkedOrbKey: DISCOUNTS_ORB_KEY,
    sortOrder: 1,
    name: "تخفیف‌ها",
    dockLabel: "تخفیف‌ها",
    title: "تخفیف‌های ویژه‌ی کارزار",
    subtitle: "پیشنهادهای ویژه برای خرید به‌صرفه‌تر ابزار و تجهیزات صنعتی.",
    desktopImage: `${HERO_CALIBRATED_ASSET_DIR}/H01-special-offers-desktop-16x9.webp`,
    mobileImage: `${HERO_CALIBRATED_ASSET_DIR}/H01-special-offers-mobile-4x3.webp`,
    desktopFocal: "left 58%",
    mobileFocal: "36% 62%",
    primaryCta: { label: "مشاهده تخفیف‌ها", href: DISCOUNTS_CATALOG_HREF },
  },
  {
    id: "slide_h02_measuring",
    linkedOrbKey: "metrology",
    sortOrder: 2,
    name: "اندازه‌گیری",
    dockLabel: "اندازه‌گیری",
    title: "ابزار اندازه‌گیری",
    subtitle: "مجموعه‌ای متنوع از ابزارهای اندازه‌گیری برای سنجش دقیق و کنترل کیفیت.",
    desktopImage: `${HERO_CALIBRATED_ASSET_DIR}/H02-measuring-tools-desktop-16x9.webp`,
    mobileImage: `${HERO_CALIBRATED_ASSET_DIR}/H02-measuring-tools-mobile-4x3.webp`,
    desktopFocal: "left 62%",
    mobileFocal: "34% 58%",
    primaryCta: {
      label: "مشاهده ابزار اندازه‌گیری",
      href: "/categories/andaze-giri",
    },
  },
  {
    id: "slide_h03_inserts",
    linkedOrbKey: "inserts",
    sortOrder: 3,
    name: "اینسرت و ابزارهای اینسرتی",
    dockLabel: "اینسرت و ابزارهای اینسرتی",
    title: "اینسرت و ابزارهای اینسرتی",
    subtitle: "انتخاب ابزار متناسب با جنس قطعه، نوع عملیات و شرایط ماشین‌کاری.",
    desktopImage: `${HERO_CALIBRATED_ASSET_DIR}/H03-inserts-turning-tools-desktop-16x9.webp`,
    mobileImage: `${HERO_CALIBRATED_ASSET_DIR}/H03-inserts-turning-tools-mobile-4x3.webp`,
    desktopFocal: "left 64%",
    mobileFocal: "40% 66%",
    primaryCta: { label: "مشاهده اینسرت‌ها", href: "/categories/insert" },
    secondaryCta: {
      label: "مشاهده ابزارهای اینسرتی",
      href: "/categories/abzar-inserti",
    },
  },
  {
    id: "slide_h04_endmills",
    linkedOrbKey: "endmills",
    sortOrder: 4,
    name: "فرز انگشتی",
    dockLabel: "فرز انگشتی",
    title: "فرز انگشتی",
    subtitle: "هندسه‌ها و ابعاد متنوع برای ماشین‌کاری قطعات و سطوح مختلف.",
    desktopImage: `${HERO_CALIBRATED_ASSET_DIR}/H04-end-mills-desktop-16x9.webp`,
    mobileImage: `${HERO_CALIBRATED_ASSET_DIR}/H04-end-mills-mobile-4x3.webp`,
    desktopFocal: "left center",
    mobileFocal: "42% 54%",
    primaryCta: {
      label: "مشاهده فرزهای انگشتی",
      href: "/categories/farz-angoshti",
    },
  },
  {
    id: "slide_h05_machines",
    linkedOrbKey: "industrial-machines",
    sortOrder: 5,
    name: "دستگاه‌های صنعتی",
    dockLabel: "دستگاه‌های صنعتی",
    title: "دستگاه‌های صنعتی",
    subtitle: "تجهیز کارگاه و خط تولید با دستگاه‌های متناسب با نیازهای صنعتی شما.",
    desktopImage: `${HERO_CALIBRATED_ASSET_DIR}/H05-industrial-machines-desktop-16x9.webp`,
    mobileImage: `${HERO_CALIBRATED_ASSET_DIR}/H05-industrial-machines-mobile-4x3.webp`,
    desktopFocal: "left 56%",
    mobileFocal: "38% 60%",
    primaryCta: {
      label: "مشاهده دستگاه‌های صنعتی",
      href: "/categories/dastgah-sanati",
    },
  },
];

export const HERO_CAMPAIGN_FEATURED_KEYS: HeroCampaignSlideKey[] =
  HERO_CAMPAIGN_FIVE_SLIDES.map((s) => s.linkedOrbKey);

const SHARED_OVERLAY = {
  mode: "gradient" as const,
  solidColor: "rgba(12,12,12,0.55)",
  gradientFrom: "rgba(8,8,8,0.12)",
  gradientTo: "rgba(8,8,8,0.58)",
  gradientAngle: 105,
  opacity: 0.82,
};

const SHARED_TYPO = {
  titleColor: "#FFFFFF",
  subtitleColor: "rgba(255,255,255,0.9)",
  titleSize: 44,
  subtitleSize: 17,
  align: "start" as const,
  position: { x: 6, y: 28 },
  maxWidth: 460,
};

function slideFromCampaign(def: HeroCampaignSlideDef): DesignedHeroSlide {
  const buttons: DesignedHeroSlide["config"]["buttons"] = [
    {
      id: `btn_${def.id}`,
      label: def.primaryCta.label,
      variant: "solid",
      bgColor: "#D02327",
      textColor: "#FFFFFF",
      borderRadius: 12,
      position: { x: 6, y: 58 },
      action: { type: "href", value: def.primaryCta.href },
      stylePreset: "primary",
      sizePreset: "lg",
    },
  ];
  if (def.secondaryCta) {
    buttons.push({
      id: `btn_${def.id}_secondary`,
      label: def.secondaryCta.label,
      variant: "solid",
      bgColor: "#5E5F5E",
      textColor: "#FFFFFF",
      borderRadius: 12,
      position: { x: 6, y: 68 },
      action: { type: "href", value: def.secondaryCta.href },
      stylePreset: "soft",
      sizePreset: "lg",
    });
  }
  return {
    id: def.id,
    name: def.name,
    sortOrder: def.sortOrder,
    isActive: true,
    mobilePreset: "balanced",
    config: {
      version: 1,
      minHeight: 760,
      animation: "fade-up",
      linkedOrbKey: def.linkedOrbKey,
      background: {
        mode: "image",
        imageUrl: def.desktopImage,
        mobileImageUrl: def.mobileImage,
        color: "#121212",
        focal: def.desktopFocal,
      },
      overlay: SHARED_OVERLAY,
      typography: {
        ...SHARED_TYPO,
        title: def.title,
        subtitle: def.subtitle,
      },
      buttons,
      badges: [],
      carousel: {
        enabled: false,
        categorySlug: "",
        categoryLabel: "",
        position: { x: 52, y: 62 },
        maxItems: 4,
      },
    },
  };
}

/** Published storefront pack — five slides + full category dock with featured 0–4. */
export function buildFiveHeroPublishedPack(
  publishedAt: string | null = "2026-10-21T09:18:00.000Z",
): DesignedHeroPack {
  const dockCategories = [
    {
      key: DISCOUNTS_SPECIAL.key,
      name: DISCOUNTS_SPECIAL.name,
      icon: CATEGORY_ICON_BY_SLUG[DISCOUNTS_SPECIAL.iconSlug]!,
      productCount: 0,
      heroImage: DISCOUNTS_SPECIAL.heroImage,
      subtitle: DISCOUNTS_SPECIAL.subtitle,
      ctaLabel: DISCOUNTS_SPECIAL.ctaLabel,
      featuredOrder: DISCOUNTS_SPECIAL.featuredOrder,
      slugHint: DISCOUNTS_SPECIAL.slug,
      special: true,
    },
    ...FINAL_L1_CATEGORIES.map((cat) => ({
      key: cat.key,
      name: cat.heroDockLabel ?? cat.name,
      icon: CATEGORY_ICON_BY_SLUG[cat.iconSlug] ?? `/category-icons/${cat.slug}.png`,
      productCount: 0,
      heroImage: cat.heroImage,
      subtitle: cat.subtitle,
      ctaLabel: cat.ctaLabel,
      featuredOrder: cat.featuredOrder,
      slugHint: cat.slug,
    })),
  ];

  return {
    version: 1,
    publishedAt,
    mobilePreset: "balanced",
    categoryDock: { categories: dockCategories },
    slides: HERO_CAMPAIGN_FIVE_SLIDES.map(slideFromCampaign),
  };
}
