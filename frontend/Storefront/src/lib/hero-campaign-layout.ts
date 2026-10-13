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

export type CampaignMediaLayout = {
  desktopFocal: string;
  /** Product-preserving crop in the dedicated mobile media band. */
  compactFocal: string;
  /** width / height for the mobile media region. */
  compactAspect: number;
};

const DEFAULT_COMPACT_ASPECT = 4 / 3;

export function campaignMediaForSlide(slideId: string): CampaignMediaLayout {
  const def = defById.get(slideId);
  if (!def) {
    return {
      desktopFocal: "left 40%",
      compactFocal: "left center",
      compactAspect: DEFAULT_COMPACT_ASPECT,
    };
  }
  return {
    desktopFocal: def.focal,
    compactFocal: def.focal.replace(/^left\s+/i, "left "),
    compactAspect: compactAspectFor(def),
  };
}

/** Wider media band when 4:3 would clip the main product group. */
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

export function campaignDesktopImageUrl(slide: DesignedHeroSlide): string {
  return slide.config.background.imageUrl;
}
