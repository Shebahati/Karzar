import type {
  BuiltInHomeSectionType,
  CategoryCarouselSection,
  HomeLayoutPack,
  HomeLayoutSection,
} from "./types";
import { HOME_LAYOUT_VERSION } from "./types";

export const BUILTIN_SECTION_LABELS: Record<BuiltInHomeSectionType, string> = {
  discounts: "پرتخفیف‌ها",
  bestsellers: "پرفروش‌ها",
  features: "چرا کارزار (ویژگی‌ها)",
  trust: "نوار اعتماد",
  brands: "برندها",
  articles: "مقالات",
  contact: "تماس / تیکت",
};

export const BUILTIN_SECTION_TYPES = Object.keys(
  BUILTIN_SECTION_LABELS,
) as BuiltInHomeSectionType[];

export function createSectionId(prefix = "sec"): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID().slice(0, 8)}`;
  }
  return `${prefix}-${Date.now().toString(36)}`;
}

/** Seed matching current desktop home order (hero fixed, not listed). */
export function createDefaultHomeLayoutPack(): HomeLayoutPack {
  return {
    version: HOME_LAYOUT_VERSION,
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
        subtitle:
          "کولیس، میکرومتر و گیج‌های صنعتی از برندهای معتبر — کنترل کیفیت مطمئن برای خط تولید شما",
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
        subtitle:
          "ماشین‌ها و تجهیزات صنعتی برای ارتقای ظرفیت کارگاه — انتخاب تخصصی، پشتیبانی کارزاری",
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

export function createCategoryCarouselSection(
  partial?: Partial<Omit<CategoryCarouselSection, "type">>,
): CategoryCarouselSection {
  return {
    id: partial?.id ?? createSectionId("carousel"),
    type: "category_carousel",
    enabled: partial?.enabled ?? true,
    title: partial?.title ?? "",
    subtitle: partial?.subtitle ?? "",
    ctaLabel: partial?.ctaLabel ?? "مشاهده همه",
    categoryId: partial?.categoryId ?? 0,
    categorySlug: partial?.categorySlug,
    limit: partial?.limit ?? 12,
  };
}

function isBuiltInType(type: string): type is BuiltInHomeSectionType {
  return (BUILTIN_SECTION_TYPES as string[]).includes(type);
}

export function normalizeHomeLayoutPack(raw: unknown): HomeLayoutPack {
  const fallback = createDefaultHomeLayoutPack();
  if (!raw || typeof raw !== "object") return fallback;

  const data = raw as Partial<HomeLayoutPack>;
  if (data.version !== HOME_LAYOUT_VERSION || !Array.isArray(data.sections)) {
    return fallback;
  }

  const sections: HomeLayoutSection[] = [];
  for (const item of data.sections) {
    if (!item || typeof item !== "object") continue;
    const s = item as Partial<HomeLayoutSection>;
    if (typeof s.id !== "string" || !s.id || typeof s.type !== "string") continue;

    if (s.type === "category_carousel") {
      const title = typeof s.title === "string" ? s.title.trim() : "";
      sections.push({
        id: s.id,
        type: "category_carousel",
        enabled: s.enabled !== false,
        title,
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

    if (isBuiltInType(s.type)) {
      sections.push({
        id: s.id,
        type: s.type,
        enabled: s.enabled !== false,
      });
    }
  }

  if (!sections.length) return fallback;

  return {
    version: HOME_LAYOUT_VERSION,
    publishedAt:
      typeof data.publishedAt === "string" ? data.publishedAt : null,
    sections,
  };
}

export type HomeLayoutIssue = { sectionId?: string; message: string };

export function validateHomeLayoutPack(pack: HomeLayoutPack): HomeLayoutIssue[] {
  const issues: HomeLayoutIssue[] = [];
  const ids = new Set<string>();

  for (const section of pack.sections) {
    if (ids.has(section.id)) {
      issues.push({ sectionId: section.id, message: "شناسه بخش تکراری است" });
    }
    ids.add(section.id);

    if (section.type === "category_carousel") {
      if (!section.title.trim()) {
        issues.push({
          sectionId: section.id,
          message: "عنوان کروسل دسته الزامی است",
        });
      }
      if (!(section.categoryId > 0) && !section.categorySlug?.trim()) {
        issues.push({
          sectionId: section.id,
          message: "دسته را انتخاب کنید",
        });
      }
    }
  }

  return issues;
}
