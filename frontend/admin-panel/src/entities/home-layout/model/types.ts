/** Home page layout pack — published as `home-layout.json` (hero stays separate). */

export const HOME_LAYOUT_VERSION = 1 as const;

export type BuiltInHomeSectionType =
  | "discounts"
  | "bestsellers"
  | "features"
  | "trust"
  | "brands"
  | "articles"
  | "contact";

export type HomeSectionType = BuiltInHomeSectionType | "category_carousel";

export type BuiltInHomeSection = {
  id: string;
  type: BuiltInHomeSectionType;
  enabled: boolean;
};

export type CategoryCarouselSection = {
  id: string;
  type: "category_carousel";
  enabled: boolean;
  title: string;
  subtitle?: string;
  ctaLabel?: string;
  /** Live category id; 0 means resolve via categorySlug on Storefront. */
  categoryId: number;
  categorySlug?: string;
  limit?: number;
};

export type HomeLayoutSection = BuiltInHomeSection | CategoryCarouselSection;

export type HomeLayoutPack = {
  version: typeof HOME_LAYOUT_VERSION;
  publishedAt: string | null;
  sections: HomeLayoutSection[];
};
