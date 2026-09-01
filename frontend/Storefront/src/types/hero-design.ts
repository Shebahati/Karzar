/** Published hero design pack (shared with admin builder). */

export type DesignedHeroAnimation =
  | "none"
  | "fade-up"
  | "fade-in"
  | "slide-in"
  | "zoom-soft"
  | "float"
  | "stagger-up";

export interface DesignedHeroPosition {
  x: number;
  y: number;
}

export interface DesignedHeroConfig {
  version: 1;
  background: {
    mode: "image" | "color";
    imageUrl: string;
    /** Optional mobile-specific art-directed asset (desktop uses imageUrl). */
    mobileImageUrl?: string;
    color: string;
    focal: string;
  };
  overlay: {
    mode: "solid" | "gradient";
    solidColor: string;
    gradientFrom: string;
    gradientTo: string;
    gradientAngle: number;
    opacity: number;
  };
  typography: {
    title: string;
    subtitle: string;
    titleColor: string;
    subtitleColor: string;
    titleSize: number;
    subtitleSize: number;
    align: "start" | "center" | "end";
    position: DesignedHeroPosition;
    maxWidth: number;
  };
  buttons: Array<{
    id: string;
    label: string;
    variant: "solid" | "outline" | "ghost" | "glass";
    bgColor: string;
    textColor: string;
    borderRadius: number;
    position: DesignedHeroPosition;
    action: { type: "href" | "modal" | "fn"; value: string };
    stylePreset?: "primary" | "soft" | "on-dark-glass" | "on-dark-outline";
    sizePreset?: "sm" | "md" | "lg" | "pill";
  }>;
  badges: Array<{
    id: string;
    kind: string;
    style: "pill" | "ribbon" | "chip" | "banner" | "stamp";
    label: string;
    meta?: string;
    position: DesignedHeroPosition;
    animated: boolean;
  }>;
  carousel: {
    enabled: boolean;
    categorySlug: string;
    categoryLabel: string;
    position: DesignedHeroPosition;
    maxItems: number;
    previewTitles?: string[];
    stylePreset?: string;
    layoutPreset?: string;
    productIds?: number[];
    categoryId?: number | null;
  };
  animation: DesignedHeroAnimation;
  minHeight: number;
  linkedOrbKey?: string | null;
}

export interface DesignedHeroSlide {
  id: string;
  name: string;
  sortOrder: number;
  isActive: boolean;
  /** Per-slide mobile composition; falls back to pack.mobilePreset */
  mobilePreset?: "balanced" | "copy-focus" | "media-focus" | "dock-first";
  config: DesignedHeroConfig;
}

export interface DesignedHeroPack {
  version: 1;
  publishedAt: string | null;
  slides: DesignedHeroSlide[];
  mobilePreset?: "balanced" | "copy-focus" | "media-focus" | "dock-first";
  /** Optional published category dock (12 orbs + featured order) */
  categoryDock?: {
    categories: Array<{
      key: string;
      name: string;
      icon: string;
      productCount: number;
      heroImage: string;
      subtitle: string;
      ctaLabel: string;
      featuredOrder: number | null;
      slugHint: string;
      categoryId?: number;
      special?: boolean;
    }>;
  };
}
