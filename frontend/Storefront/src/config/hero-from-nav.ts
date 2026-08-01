/**
 * Build storefront hero slides 1:1 with enabled megamenu nav groups.
 *
 * Image priority: CMS slide override (matched by group) → curated static
 * fallback by group slug. Category packshots are skipped for full-bleed
 * hero (they suit cards, not RTL left-weighted hero composition).
 * Copy priority: CMS override → curated defaults keyed by group slug.
 */

import {
  buildNavGroups,
  categoryHref,
  type CategoryLike,
  type NavGroupDef,
  NAV_GROUPS,
} from "@/config/nav-groups";
import type { HeroSlide } from "@/types/content";

export type HeroCategoryNode = CategoryLike & {
  slug?: string | null;
  image_url?: string | null;
};

export interface NavHeroCopy {
  subtitle: string;
  cta_label: string;
  /** Fallback when no category image is available. */
  fallbackImage: string;
}

/**
 * Curated Persian copy + image fallbacks for locked IA groups.
 * Fallback photos are left-weighted (subject left, quieter right) so RTL
 * hero copy on the right sits over empty space.
 */
export const NAV_HERO_COPY: Record<string, NavHeroCopy> = {
  metrology: {
    subtitle:
      "کولیس، میکرومتر و گیج‌های صنعتی از برندهای معتبر — موجودی و استعلام برای خط تولید شما",
    cta_label: "مشاهده اندازه‌گیری",
    fallbackImage: "/images/hero/hero-metrology-left.jpg",
  },
  cutting: {
    subtitle: "اینسرت، مته، قلاویز و ابزار انگشتی — انتخاب سریع برای براده‌برداری دقیق",
    cta_label: "مشاهده براده‌برداری",
    fallbackImage: "/images/hero/hero-cutting-left.jpg",
  },
  holding: {
    subtitle: "ابزارگیر، کولت و سیستم‌های گیرش ماشین‌ابزار برای پایداری بیشتر در ماشینکاری",
    cta_label: "مشاهده ابزارگیری",
    fallbackImage: "/images/hero/hero-holding-left.jpg",
  },
  machines: {
    subtitle: "ماشین‌ها و تجهیزات صنعتی برای تجهیز کارگاه و خط تولید",
    cta_label: "مشاهده ماشین‌ها",
    fallbackImage: "/images/hero/hero-machines-left.jpg",
  },
  accessories: {
    subtitle: "لوازم جانبی و مواد مصرفی کارگاهی برای تکمیل ابزارخانه و نگهداری روزمره",
    cta_label: "مشاهده لوازم جانبی",
    fallbackImage: "/images/hero/hero-accessories-left.jpg",
  },
};

const DEFAULT_COPY: NavHeroCopy = {
  subtitle: "کاتالوگ تخصصی ابزار صنعتی کارزار — از اندازه‌گیری تا براده‌برداری",
  cta_label: "مشاهده دسته‌بندی",
  fallbackImage: "/images/hero/hero-metrology-left.jpg",
};

function normalizeFa(s: string): string {
  return s.trim().replace(/\u200c/g, "").replace(/ي/g, "ی").replace(/ك/g, "ک").toLowerCase();
}

/** Match a CMS slide to a nav group by title/cta overlap. */
export function matchCmsSlideToGroup(
  slides: HeroSlide[],
  groupId: string,
  groupLabel: string,
  usedIds: Set<number>,
): HeroSlide | undefined {
  const label = normalizeFa(groupLabel);
  const idHint = normalizeFa(groupId);

  const ranked = slides
    .filter((s) => !usedIds.has(s.id))
    .map((s) => {
      const title = normalizeFa(s.title);
      const href = normalizeFa(s.cta_href ?? "");
      let score = 0;
      if (title === label || title.includes(label) || label.includes(title)) score += 4;
      if (title.includes(idHint) || href.includes(idHint)) score += 2;
      if (href.includes("categor") || href.includes("catalog")) score += 1;
      return { slide: s, score };
    })
    .filter((x) => x.score >= 2)
    .sort((a, b) => b.score - a.score);

  return ranked[0]?.slide;
}


function pickHref(roots: HeroCategoryNode[]): string {
  if (roots.length >= 1) return categoryHref(roots[0]);
  return "/catalog";
}

/**
 * One slide per enabled megamenu group (non-empty roots only).
 * CMS slides optionally override image/copy when they match a group.
 */
export function buildHeroSlidesFromNavGroups(
  roots: HeroCategoryNode[],
  groups: NavGroupDef[] = NAV_GROUPS,
  cmsSlides: HeroSlide[] = [],
): HeroSlide[] {
  const resolved = buildNavGroups(roots, groups);
  const usedCms = new Set<number>();

  return resolved.map((group, index) => {
    const copy = NAV_HERO_COPY[group.id] ?? DEFAULT_COPY;
    const cms = matchCmsSlideToGroup(cmsSlides, group.id, group.label, usedCms);
    if (cms) usedCms.add(cms.id);

    const title = cms?.title?.trim() || group.label;
    const subtitle = cms?.subtitle?.trim() || copy.subtitle;
    const cta_label = cms?.cta_label?.trim() || copy.cta_label;
    const cta_href = cms?.cta_href?.trim() || pickHref(group.roots as HeroCategoryNode[]);
    const image = cms?.image?.trim() || copy.fallbackImage;

    return {
      id: cms?.id ?? index + 1,
      title,
      subtitle,
      cta_label,
      cta_href,
      image,
      accent: cms?.accent?.trim() || "#D02327",
    };
  });
}
