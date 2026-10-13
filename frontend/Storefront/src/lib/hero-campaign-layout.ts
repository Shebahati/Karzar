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

export type CampaignMediaLayout = {
  desktopFocal: string;
  /** Crop anchor for the dedicated compact media band (independent of desktop). */
  mobileFocal: string;
  /** Landscape width/height for the compact media band (interim `-1280.webp` crop). */
  compactAspect: number;
  /** Desktop copy anchor — verified empty region per slide after cover crop. */
  desktopCopyClass: string;
  /** Compact copy sits below the media band (never over product geometry). */
  compactCopyClass: string;
};

const DEFAULT_COMPACT_ASPECT = 4 / 3;

/** Master width for compact-band WebP exports (interim landscape + future portrait). */
export const COMPACT_BAND_ART_WIDTH_PX = 1280;

/** Portrait acceptance target when dedicated mobile art replaces landscape interim. */
export const COMPACT_BAND_PORTRAIT_ASPECT = 3 / 4;

export const COMPACT_BAND_PORTRAIT_HEIGHT_PX = Math.round(
  COMPACT_BAND_ART_WIDTH_PX / COMPACT_BAND_PORTRAIT_ASPECT,
);

const DEFAULT_DESKTOP_COPY =
  "right-[clamp(2rem,7vw,8rem)] top-1/2 -translate-y-1/2 max-w-[min(560px,92vw)]";

const DEFAULT_COMPACT_COPY = "relative w-full px-5 pb-[max(1.25rem,env(safe-area-inset-bottom,0px))] pt-4";

function desktopCopyClassFor(def: HeroCampaignSlideDef): string {
  switch (def.linkedOrbKey) {
    case "discounts":
      // Lift copy above the drill shank / rear region at tall desktop ratios.
      return "right-[clamp(2.25rem,7.5vw,9rem)] top-[34%] max-w-[min(520px,90vw)]";
    case "endmills":
      // Keep subtitle off the translucent tool tube on the right product group.
      return "right-[clamp(2.5rem,8vw,9.5rem)] top-[38%] max-w-[min(500px,88vw)]";
    case "industrial-machines":
      return "right-[clamp(2rem,7vw,8.5rem)] top-[36%] max-w-[min(540px,90vw)]";
    default:
      return DEFAULT_DESKTOP_COPY;
  }
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

export function campaignMediaForSlide(slideId: string): CampaignMediaLayout {
  const def = defById.get(slideId);
  if (!def) {
    return {
      desktopFocal: "left 40%",
      mobileFocal: "28% center",
      compactAspect: DEFAULT_COMPACT_ASPECT,
      desktopCopyClass: DEFAULT_DESKTOP_COPY,
      compactCopyClass: DEFAULT_COMPACT_COPY,
    };
  }
  return {
    desktopFocal: def.desktopFocal,
    mobileFocal: def.mobileFocal,
    compactAspect: compactAspectFor(def),
    desktopCopyClass: desktopCopyClassFor(def),
    compactCopyClass: DEFAULT_COMPACT_COPY,
  };
}

export function campaignDesktopImageUrl(slide: DesignedHeroSlide): string {
  return slide.config.background.imageUrl;
}
