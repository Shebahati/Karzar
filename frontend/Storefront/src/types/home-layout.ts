/** Consumer types for `/home-layout.json` (mirrors admin HomeLayoutPack). */

export type BuiltInHomeSectionType =
  | "discounts"
  | "bestsellers"
  | "features"
  | "trust"
  | "brands"
  | "articles"
  | "contact";

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
  categoryId: number;
  categorySlug?: string;
  limit?: number;
};

export type HomeLayoutSection = BuiltInHomeSection | CategoryCarouselSection;

export type HomeLayoutPack = {
  version: 1;
  publishedAt: string | null;
  sections: HomeLayoutSection[];
};

const BUILTIN = new Set<string>([
  "discounts",
  "bestsellers",
  "features",
  "trust",
  "brands",
  "articles",
  "contact",
]);

/** Hardcoded fallback matching pre-CMS desktop home order. */
export function defaultHomeLayoutPack(): HomeLayoutPack {
  return {
    version: 1,
    publishedAt: null,
    sections: [
      { id: "discounts", type: "discounts", enabled: true },
      { id: "bestsellers", type: "bestsellers", enabled: true },
      { id: "features", type: "features", enabled: true },
      { id: "trust", type: "trust", enabled: true },
      {
        id: "carousel-metrology",
        type: "category_carousel",
        enabled: true,
        title: "اندازه‌گیری",
        subtitle: "کولیس، میکرومتر و گیج‌های صنعتی از برندهای معتبر",
        ctaLabel: "مشاهده اندازه‌گیری",
        categoryId: 0,
        categorySlug: "andaze-giri",
        limit: 12,
      },
      {
        id: "carousel-industrial",
        type: "category_carousel",
        enabled: true,
        title: "دستگاه‌های صنعتی",
        subtitle: "ماشین‌ها و تجهیزات صنعتی برای ارتقای ظرفیت کارگاه",
        ctaLabel: "مشاهده دستگاه‌ها",
        categoryId: 0,
        categorySlug: "dastgah-sanati",
        limit: 12,
      },
      { id: "brands", type: "brands", enabled: true },
      { id: "articles", type: "articles", enabled: true },
      { id: "contact", type: "contact", enabled: true },
    ],
  };
}

export function normalizeHomeLayoutPack(raw: unknown): HomeLayoutPack {
  const fallback = defaultHomeLayoutPack();
  if (!raw || typeof raw !== "object") return fallback;
  const data = raw as Partial<HomeLayoutPack>;
  if (data.version !== 1 || !Array.isArray(data.sections) || !data.sections.length) {
    return fallback;
  }

  const sections: HomeLayoutSection[] = [];
  for (const item of data.sections) {
    if (!item || typeof item !== "object") continue;
    const s = item as Partial<HomeLayoutSection>;
    if (typeof s.id !== "string" || !s.id || typeof s.type !== "string") continue;

    if (s.type === "category_carousel") {
      sections.push({
        id: s.id,
        type: "category_carousel",
        enabled: s.enabled !== false,
        title: typeof s.title === "string" ? s.title : "",
        subtitle: typeof s.subtitle === "string" ? s.subtitle : undefined,
        ctaLabel: typeof s.ctaLabel === "string" ? s.ctaLabel : undefined,
        categoryId:
          typeof s.categoryId === "number" && Number.isFinite(s.categoryId)
            ? s.categoryId
            : 0,
        categorySlug:
          typeof s.categorySlug === "string" && s.categorySlug.trim()
            ? s.categorySlug.trim()
            : undefined,
        limit:
          typeof s.limit === "number" && s.limit > 0
            ? Math.min(48, Math.floor(s.limit))
            : 12,
      });
      continue;
    }

    if (BUILTIN.has(s.type)) {
      sections.push({
        id: s.id,
        type: s.type as BuiltInHomeSectionType,
        enabled: s.enabled !== false,
      });
    }
  }

  return sections.length
    ? {
        version: 1,
        publishedAt:
          typeof data.publishedAt === "string" ? data.publishedAt : null,
        sections,
      }
    : fallback;
}
