export type * from "./model/types";
export {
  BRAND_COLOR_PRESETS,
  DEFAULT_CATEGORY_DOCK,
  DEFAULT_HERO_CONFIG,
  DISCOUNTS_CATALOG_HREF,
  DISCOUNTS_ORB_KEY,
  HERO_ANIMATION_PRESETS,
  HERO_BADGE_KINDS,
  HERO_BADGE_STYLES,
  HERO_FEATURED_SLOT_COUNT,
  HERO_SLIDE_SLOT_COUNT,
  configFromOrb,
  createDefaultConfig,
  createDefaultProject,
  createDiscountsOrb,
  createEmptySlideSlot,
  createId,
  createSlide,
  categoryDockFromRoots,
  densifyFeaturedOrders,
  featuredDockCategories,
  featuredIndexForSlide,
  firstEmptyFeaturedSlot,
  isSlideFilled,
  isSpecialDockOrb,
  normalizeHeroProject,
  normalizeHeroSlides,
  orbFromTreeRoot,
  slideIdForOrbKey,
  syncDockWithRoots,
  validateHeroProject,
} from "./model/defaults";
export type { DockSyncResult, HeroProjectIssue } from "./model/defaults";
export { CURATED_HERO_SEEDS, curatedSlidesFromDock, configFromCuratedSeed } from "./model/curated-slides";
export {
  DS_BUTTON_SIZES,
  DS_BUTTON_STYLES,
  DS_CAROUSEL_LAYOUTS,
  DS_CAROUSEL_STYLES,
  MOBILE_COMPOSE_PRESETS,
  buttonSizeCss,
  buttonStyleCss,
} from "./model/presets";
export { composeHeroForMobile } from "./model/mobile-compose";
export type { MobileComposeView, MobileDockScale } from "./model/mobile-compose";
export { useHeroBuilderStore } from "./model/store";
