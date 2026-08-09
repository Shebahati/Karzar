/**
 * Static storefront pages managed from admin CMS:
 * contact / about / terms / privacy.
 *
 * Persistence today: browser localStorage via `staticPagesService`.
 * Storefront still serves hardcoded FE content — do NOT treat drafts as live.
 *
 * When BE ships page endpoints, swap only the service; keep these shapes stable
 * (aligned with Storefront `LegalSection` + page meta).
 */

export type StaticPageSlug = "contact" | "about" | "terms" | "privacy";

/** Mirrors Storefront `LegalSection` in legal-page-shell.tsx */
export type StaticPageSection = {
  id: string;
  title: string;
  paragraphs: string[];
  bullets?: string[];
  note?: string;
  related?: { label: string; href: string }[];
};

/** Contact identity — currently live in Storefront `store-location.ts` */
export type StaticContactFields = {
  phoneDisplay: string;
  phoneE164: string;
  email: string;
  address: string;
  addressMapCaption: string;
  telegramUrl: string;
  whatsappUrl: string;
  instagramUrl: string;
};

export type StaticPageDocument = {
  slug: StaticPageSlug;
  /** Admin + storefront H1 */
  title: string;
  /** Short eyebrow / label above title when applicable */
  eyebrow: string;
  intro: string;
  updatedLabel?: string;
  sections: StaticPageSection[];
  /** Only used for `contact` */
  contact?: StaticContactFields;
  /** ISO timestamp of last local save */
  updatedAt: string;
};

export type StaticPagesStore = {
  version: 1;
  pages: Record<StaticPageSlug, StaticPageDocument>;
};

export const STATIC_PAGE_META: Record<
  StaticPageSlug,
  { label: string; hrefPreview: string; description: string }
> = {
  contact: {
    label: "تماس با ما",
    hrefPreview: "/contact",
    description: "اطلاعات تماس، نشانی و متن معرفی صفحه",
  },
  about: {
    label: "درباره ما",
    hrefPreview: "/about",
    description: "داستان برند، ارزش‌ها و مسیر رشد",
  },
  terms: {
    label: "قوانین",
    hrefPreview: "/terms",
    description: "شرایط استفاده از فروشگاه",
  },
  privacy: {
    label: "حریم شخصی",
    hrefPreview: "/privacy",
    description: "سیاست حفظ حریم خصوصی",
  },
};

/**
 * Future BE contract (stub). When live, `staticPagesService` should call:
 * - GET    /cms/static-pages
 * - GET    /cms/static-pages/:slug
 * - PUT    /cms/static-pages/:slug   body: StaticPageDocument (sans local-only fields)
 * - POST   /cms/static-pages/:slug/publish
 *
 * Suggested published payload for Storefront:
 * `{ slug, title, eyebrow, intro, updatedLabel, sections, contact? }`
 * with Storefront fallback to hardcoded TS if fetch fails.
 */
export type StaticPagesApiStub = {
  list(): Promise<StaticPageDocument[]>;
  get(slug: StaticPageSlug): Promise<StaticPageDocument>;
  save(doc: StaticPageDocument): Promise<StaticPageDocument>;
  publish(slug: StaticPageSlug): Promise<StaticPageDocument>;
};
