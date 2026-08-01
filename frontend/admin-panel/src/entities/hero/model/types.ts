/** Hero Design Builder — configuration schema (frontend-owned). */

export type OverlayMode = "solid" | "gradient";
export type TextAlign = "start" | "center" | "end";
export type ButtonVariant = "solid" | "outline" | "ghost" | "glass";
export type ButtonActionType = "href" | "modal" | "fn";
export type PreviewDevice = "desktop" | "tablet" | "mobile";
export type HeroLayerKind = "typography" | "button" | "badge" | "carousel";

export type DsButtonStyle = "primary" | "soft" | "on-dark-glass" | "on-dark-outline";
export type DsButtonSize = "sm" | "md" | "lg" | "pill";
export type DsCarouselStyle = "rail-soft" | "cards-elevated" | "strip-minimal" | "spotlight";
export type DsCarouselLayout = "row-compact" | "row-comfortable" | "row-large" | "stack";
export type MobileComposePreset = "balanced" | "copy-focus" | "media-focus" | "dock-first";

export type HeroAnimationPreset =
  | "none"
  | "fade-up"
  | "fade-in"
  | "slide-in"
  | "zoom-soft"
  | "float"
  | "stagger-up";

export type HeroBadgeKind =
  | "discount"
  | "flash_sale"
  | "campaign"
  | "new_arrival"
  | "limited"
  | "free_shipping"
  | "trust";

export type HeroBadgeStyle = "pill" | "ribbon" | "chip" | "banner" | "stamp";

export interface HeroPosition {
  x: number;
  y: number;
}

export interface HeroBackground {
  mode: "image" | "color";
  imageUrl: string;
  color: string;
  /** CSS object-position, e.g. "center", "left 40%" */
  focal: string;
}

export interface HeroOverlay {
  mode: OverlayMode;
  solidColor: string;
  gradientFrom: string;
  gradientTo: string;
  gradientAngle: number;
  opacity: number;
}

export interface HeroTypography {
  title: string;
  subtitle: string;
  titleColor: string;
  subtitleColor: string;
  titleSize: number;
  subtitleSize: number;
  align: TextAlign;
  position: HeroPosition;
  maxWidth: number;
}

export interface HeroButtonAction {
  type: ButtonActionType;
  value: string;
}

export interface HeroButton {
  id: string;
  label: string;
  /** @deprecated prefer stylePreset */
  variant: ButtonVariant;
  /** @deprecated prefer stylePreset */
  bgColor: string;
  textColor: string;
  borderRadius: number;
  position: HeroPosition;
  action: HeroButtonAction;
  stylePreset?: DsButtonStyle;
  sizePreset?: DsButtonSize;
}

export interface HeroBadge {
  id: string;
  kind: HeroBadgeKind;
  style: HeroBadgeStyle;
  label: string;
  meta?: string;
  position: HeroPosition;
  animated: boolean;
}

export interface HeroCarouselWidget {
  enabled: boolean;
  categorySlug: string;
  categoryLabel: string;
  position: HeroPosition;
  maxItems: number;
  previewTitles: string[];
  stylePreset?: DsCarouselStyle;
  layoutPreset?: DsCarouselLayout;
  /** Explicit product ids for storefront resolve */
  productIds?: number[];
  categoryId?: number | null;
}

/** One category in the glass orb dock (storefront hero). */
export interface HeroOrbCategory {
  key: string;
  name: string;
  icon: string;
  productCount: number;
  heroImage: string;
  subtitle: string;
  ctaLabel: string;
  /** 0–5 featured dock slots; null = expand-menu only */
  featuredOrder: number | null;
  slugHint: string;
  /** Live taxonomy id when synced from DB */
  categoryId?: number;
}

export interface HeroCategoryDock {
  categories: HeroOrbCategory[];
}

export interface HeroBuilderConfig {
  version: 1;
  background: HeroBackground;
  overlay: HeroOverlay;
  typography: HeroTypography;
  buttons: HeroButton[];
  badges: HeroBadge[];
  carousel: HeroCarouselWidget;
  animation: HeroAnimationPreset;
  minHeight: number;
  /** Linked orb key for slide↔dock sync */
  linkedOrbKey?: string | null;
}

/** One editable slide in the builder project. */
export interface HeroSlideDraft {
  id: string;
  name: string;
  sortOrder: number;
  isActive: boolean;
  /** Linked CMS slide id when synced */
  cmsId?: number;
  /** Per-slide mobile composition — overrides project.mobilePreset when set */
  mobilePreset?: MobileComposePreset;
  config: HeroBuilderConfig;
}

export interface HeroDesignProject {
  version: 1;
  activeSlideId: string;
  slides: HeroSlideDraft[];
  categoryDock: HeroCategoryDock;
  showGrid: boolean;
  snapToGrid: boolean;
  gridSize: number;
  previewDevice: PreviewDevice;
  /** Mobile composition — pick one of 4 safe layouts (no freeform mobile edit) */
  mobilePreset: MobileComposePreset;
}

export interface PublishedHeroPack {
  version: 1;
  publishedAt: string;
  slides: Array<{
    id: string;
    name: string;
    sortOrder: number;
    isActive: boolean;
    /** Per-slide mobile layout; falls back to pack.mobilePreset */
    mobilePreset?: MobileComposePreset;
    config: HeroBuilderConfig;
  }>;
  categoryDock: HeroCategoryDock;
  /** Default mobile preset when a slide omits its own */
  mobilePreset?: MobileComposePreset;
}
