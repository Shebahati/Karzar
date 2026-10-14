import {
  HERO_CAMPAIGN_FIVE_SLIDES,
  type HeroCampaignSlideDef,
} from "@/config/hero-campaign-five";
import type { DesignedHeroSlide } from "@/types/hero-design";

const CAMPAIGN_SLIDE_IDS = new Set(HERO_CAMPAIGN_FIVE_SLIDES.map((s) => s.id));

const defById = new Map<string, HeroCampaignSlideDef>(
  HERO_CAMPAIGN_FIVE_SLIDES.map((d) => [d.id, d]),
);

/** True when the active pack is the approved five-hero reborn campaign. */
export function isRebornFiveCampaign(slides: DesignedHeroSlide[]): boolean {
  if (slides.length !== 5) return false;
  return slides.every((s) => CAMPAIGN_SLIDE_IDS.has(s.id));
}

/** Stacked media + copy below ~1024px (includes portrait tablet). */
export const CAMPAIGN_COMPACT_MAX_PX = 1023;

/** Align `<picture>` mobile art with the compact composition breakpoint. */
export const CAMPAIGN_MOBILE_SOURCE_MAX_PX = CAMPAIGN_COMPACT_MAX_PX;

/** Legacy non-campaign hero mobile art (phone-only). */
export const DEFAULT_MOBILE_SOURCE_MAX_PX = 767;

/** Shared with SiteHeader overlay — copy safe area starts below header + gap. */
export const CAMPAIGN_DESKTOP_HEADER_CLEARANCE =
  "calc(5.75rem + env(safe-area-inset-top, 0px) + 1.5rem)";

export const CAMPAIGN_DESKTOP_SHELL_MAX_WIDTH_PX = 1440;

export const CAMPAIGN_DESKTOP_COPY_MAX_WIDTH = "min(520px, 38vw)";

export const CAMPAIGN_DESKTOP_SAFE_PADDING_X = "clamp(2rem, 5vw, 6rem)";

export const CAMPAIGN_DESKTOP_MIN_EDGE_MARGIN_PX = 48;

export const CAMPAIGN_COMPACT_SAFE_PADDING_X = "clamp(1.25rem, 5vw, 1.5rem)";

export const CAMPAIGN_DESKTOP_MAX_VERTICAL_NUDGE_PX = 32;

export type CampaignMediaLayout = {
  desktopFocal: string;
  mobileFocal: string;
  compactAspect: number;
  /** Small optical vertical nudge (px), not absolute positioning. */
  desktopVerticalNudgePx: number;
  compactCopyClass: string;
};

const DEFAULT_COMPACT_ASPECT = 4 / 3;

export const COMPACT_BAND_ART_WIDTH_PX = 1280;

export const COMPACT_BAND_PORTRAIT_ASPECT = 3 / 4;

export const COMPACT_BAND_PORTRAIT_HEIGHT_PX = Math.round(
  COMPACT_BAND_ART_WIDTH_PX / COMPACT_BAND_PORTRAIT_ASPECT,
);

const DEFAULT_COMPACT_COPY =
  "relative w-full px-[clamp(1.25rem,5vw,1.5rem)] pb-[max(1.5rem,env(safe-area-inset-bottom,0px))] pt-3";

function desktopVerticalNudgeFor(def: HeroCampaignSlideDef): number {
  switch (def.linkedOrbKey) {
    case "discounts":
      return -12;
    case "endmills":
      return 8;
    case "industrial-machines":
      return 4;
    case "inserts":
      return 0;
    case "metrology":
      return 0;
    default:
      return 0;
  }
}

function compactAspectFor(def: HeroCampaignSlideDef): number {
  switch (def.linkedOrbKey) {
    case "industrial-machines":
      return 16 / 10;
    case "inserts":
      return 3 / 2;
    default:
      return DEFAULT_COMPACT_ASPECT;
  }
}

export function campaignMediaForSlide(slideId: string): CampaignMediaLayout {
  const def = defById.get(slideId);
  if (!def) {
    return {
      desktopFocal: "left 40%",
      mobileFocal: "28% center",
      compactAspect: DEFAULT_COMPACT_ASPECT,
      desktopVerticalNudgePx: 0,
      compactCopyClass: DEFAULT_COMPACT_COPY,
    };
  }
  const nudge = desktopVerticalNudgeFor(def);
  return {
    desktopFocal: def.desktopFocal,
    mobileFocal: def.mobileFocal,
    compactAspect: compactAspectFor(def),
    desktopVerticalNudgePx: Math.max(
      -CAMPAIGN_DESKTOP_MAX_VERTICAL_NUDGE_PX,
      Math.min(CAMPAIGN_DESKTOP_MAX_VERTICAL_NUDGE_PX, nudge),
    ),
    compactCopyClass: DEFAULT_COMPACT_COPY,
  };
}

export function campaignDesktopImageUrl(slide: DesignedHeroSlide): string {
  return slide.config.background.imageUrl;
}

export function campaignCompactCtaCount(slide: DesignedHeroSlide): number {
  return slide.config.buttons.length;
}

export function campaignCompactMediaAspect(slide: DesignedHeroSlide): number {
  return campaignMediaForSlide(slide.id).compactAspect;
}

export function campaignTallestCompactCopySlide(
  slides: DesignedHeroSlide[],
): DesignedHeroSlide {
  return slides.reduce((tallest, slide) => {
    const count = campaignCompactCtaCount(slide);
    const tallestCount = campaignCompactCtaCount(tallest);
    if (count > tallestCount) return slide;
    if (count < tallestCount) return tallest;
    const aspect = campaignCompactMediaAspect(slide);
    const tallestAspect = campaignCompactMediaAspect(tallest);
    return aspect < tallestAspect ? slide : tallest;
  });
}

/** @deprecated Per-slide absolute copy classes removed — use desktop copy shell in CampaignHeroSlide. */
export function usesLegacyDesktopCopyPositioning(): boolean {
  return false;
}
