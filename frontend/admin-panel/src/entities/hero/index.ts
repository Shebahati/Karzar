export type * from "./model/types";
export {
  BRAND_COLOR_PRESETS,
  DEFAULT_CATEGORY_DOCK,
  DEFAULT_HERO_CONFIG,
  HERO_ANIMATION_PRESETS,
  HERO_BADGE_KINDS,
  HERO_BADGE_STYLES,
  configFromOrb,
  createDefaultConfig,
  createDefaultProject,
  createId,
  createSlide,
  categoryDockFromRoots,
  featuredDockCategories,
  orbFromTreeRoot,
  syncDockWithRoots,
} from "./model/defaults";
export type { DockSyncResult } from "./model/defaults";
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
