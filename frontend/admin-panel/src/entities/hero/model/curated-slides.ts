/**
 * Curated 6-slide hero pack — RTL-safe, responsive, design-system aligned.
 * Uses the four established left-weighted hero photos (+ accessories).
 */

import type {
  HeroBuilderConfig,
  HeroOrbCategory,
  HeroSlideDraft,
} from "./types";

function createId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 9)}`;
}

type SlideSeed = {
  orbKey: string;
  name: string;
  title: string;
  subtitle: string;
  badge?: { label: string; meta: string };
  image: string;
  focal: string;
  ctaPrimary: { label: string; href: string };
  ctaSecondary: { label: string; href: string };
  animation: HeroBuilderConfig["animation"];
  carousel?: {
    label: string;
    titles: string[];
    hrefSlug?: string;
  };
};

/** Six power slides — images cycle the classic Karzar hero set. */
export const CURATED_HERO_SEEDS: SlideSeed[] = [
  {
    orbKey: "precision-metrology",
    name: "اندازه‌گیری دقیق",
    title: "اندازه‌گیری دقیق",
    subtitle:
      "کولیس، میکرومتر و گیج‌های صنعتی از برندهای معتبر — کنترل کیفیت مطمئن برای خط تولید شما",
    badge: { label: "پرفروش مترولوژی", meta: "۲۴۸۰+" },
    image: "/images/hero/hero-metrology-left.jpg",
    focal: "left 42%",
    ctaPrimary: { label: "مشاهده اندازه‌گیری", href: "/catalog?q=%D8%A7%D9%86%D8%AF%D8%A7%D8%B2%D9%87%20%DA%AF%DB%8C%D8%B1%DB%8C%20%D8%AF%D9%82%DB%8C%D9%82" },
    ctaSecondary: { label: "استعلام قیمت", href: "/quote" },
    animation: "fade-up",
    carousel: {
      label: "منتخب مترولوژی",
      titles: ["کولیس دیجیتال", "میکرومتر بیرونی", "ساعت اندیکاتور", "بلوک سنجه"],
    },
  },
  {
    orbKey: "workholding",
    name: "ابزار گیرشی",
    title: "گیرش پایدار قطعه",
    subtitle:
      "گیره، فیکسچر و سیستم‌های نگه‌دارنده — ثبات بیشتر، لرزش کمتر، نتیجه تمیزتر در ماشین‌کاری",
    badge: { label: "موجودی گسترده", meta: "۷۷۹" },
    image: "/images/hero/hero-holding-left.jpg",
    focal: "left 40%",
    ctaPrimary: { label: "مشاهده ابزار گیرشی", href: "/catalog?q=%D8%A7%D8%A8%D8%B2%D8%A7%D8%B1%20%DA%AF%DB%8C%D8%B1%D8%B4%DB%8C" },
    ctaSecondary: { label: "کاتالوگ کامل", href: "/catalog" },
    animation: "slide-in",
  },
  {
    orbKey: "industrial-machines",
    name: "دستگاه‌های صنعتی",
    title: "تجهیز کارگاه و خط تولید",
    subtitle:
      "ماشین‌ها و تجهیزات صنعتی برای ارتقای ظرفیت کارگاه — انتخاب تخصصی، پشتیبانی کارزاری",
    badge: { label: "تجهیز حرفه‌ای", meta: "۵۸۴" },
    image: "/images/hero/hero-machines-left.jpg",
    focal: "left 38%",
    ctaPrimary: { label: "مشاهده دستگاه‌ها", href: "/catalog?q=%D8%AF%D8%B3%D8%AA%DA%AF%D8%A7%D9%87" },
    ctaSecondary: { label: "مشاوره خرید", href: "/quote" },
    animation: "zoom-soft",
  },
  {
    orbKey: "endmills",
    name: "ابزار انگشتی",
    title: "فرز انگشتی دقیق",
    subtitle:
      "ابزارهای پروفایل و فرز انگشتی برای ماشین‌کاری تمیز — از کاربید تا پوشش‌های پیشرفته",
    badge: { label: "براده‌برداری", meta: "۴۹۱" },
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "left 44%",
    ctaPrimary: { label: "مشاهده ابزار انگشتی", href: "/catalog?q=%D8%A7%D8%A8%D8%B2%D8%A7%D8%B1%20%D8%A7%D9%86%DA%AF%D8%B4%D8%AA%DB%8C" },
    ctaSecondary: { label: "استعلام موجودی", href: "/quote" },
    animation: "stagger-up",
  },
  {
    orbKey: "inserts",
    name: "اینسرت",
    title: "اینسرت کاربیدی",
    subtitle:
      "اینسرت‌های پوشش‌دار برای سطوح برش متنوع — تعویض سریع، عمر طولانی، کیفیت ثابت",
    badge: { label: "انتخاب صنعتی", meta: "۳۳۶" },
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "center left",
    ctaPrimary: { label: "مشاهده اینسرت", href: "/catalog?q=%D8%A7%DB%8C%D9%86%D8%B3%D8%B1%D8%AA" },
    ctaSecondary: { label: "مشاهده هلدر", href: "/catalog?q=%D8%A7%D8%A8%D8%B2%D8%A7%D8%B1%20%D8%A7%DB%8C%D9%86%D8%B3%D8%B1%D8%AA%DB%8C" },
    animation: "fade-up",
  },
  {
    orbKey: "industrial-accessories",
    name: "لوازم جانبی صنعتی",
    title: "لوازم جانبی کارگاهی",
    subtitle:
      "مصرفی‌ها و ملزومات روزمره ابزارخانه — تکمیل زنجیره تأمین از یک منبع معتبر",
    badge: { label: "تکمیل ابزارخانه", meta: "۲۸۹" },
    image: "/images/hero/hero-accessories-left.jpg",
    focal: "left 40%",
    ctaPrimary: { label: "مشاهده لوازم جانبی", href: "/catalog?q=%D9%84%D9%88%D8%A7%D8%B2%D9%85%20%D8%AC%D8%A7%D9%86%D8%A8%DB%8C" },
    ctaSecondary: { label: "ورود به فروشگاه", href: "/catalog" },
    animation: "fade-in",
  },
];

/** Build one responsive RTL-safe slide config from a seed. */
export function configFromCuratedSeed(seed: SlideSeed): HeroBuilderConfig {
  return {
    version: 1,
    minHeight: 720,
    animation: seed.animation,
    linkedOrbKey: seed.orbKey,
    background: {
      mode: "image",
      imageUrl: seed.image,
      color: "#121212",
      focal: seed.focal,
    },
    overlay: {
      mode: "gradient",
      // Darker toward inline-end is wrong with physical angle;
      // with insetInlineStart positioning, darken the START side (right in RTL):
      // CSS 90deg = left→right. For physical right dark: use ~270 or reverse stops.
      // We darken the right (RTL text side) with 90deg light→dark.
      solidColor: "rgba(12,12,12,0.72)",
      gradientFrom: "rgba(12,12,12,0.08)",
      gradientTo: "rgba(12,12,12,0.86)",
      gradientAngle: 90,
      opacity: 1,
    },
    typography: {
      title: seed.title,
      subtitle: seed.subtitle,
      titleColor: "#FFFFFF",
      subtitleColor: "rgba(255,255,255,0.9)",
      titleSize: 42,
      subtitleSize: 16,
      align: "start",
      // insetInlineStart — near reading start (right in RTL)
      position: { x: 5, y: 26 },
      maxWidth: 460,
    },
    buttons: [
      {
        id: createId("btn"),
        label: seed.ctaPrimary.label,
        variant: "solid",
        bgColor: "#D02327",
        textColor: "#FFFFFF",
        borderRadius: 12,
        position: { x: 5, y: 58 },
        action: { type: "href", value: seed.ctaPrimary.href },
        stylePreset: "primary",
        sizePreset: "lg",
      },
      {
        id: createId("btn"),
        label: seed.ctaSecondary.label,
        variant: "glass",
        bgColor: "rgba(255,255,255,0.12)",
        textColor: "#FFFFFF",
        borderRadius: 12,
        position: { x: 5, y: 70 },
        action: { type: "href", value: seed.ctaSecondary.href },
        stylePreset: "on-dark-glass",
        sizePreset: "md",
      },
    ],
    badges: seed.badge
      ? [
          {
            id: createId("badge"),
            kind: "campaign",
            style: "pill",
            label: seed.badge.label,
            meta: seed.badge.meta,
            position: { x: 5, y: 14 },
            animated: true,
          },
        ]
      : [],
    carousel: seed.carousel
      ? {
          enabled: true,
          categorySlug: seed.carousel.hrefSlug ?? "",
          categoryLabel: seed.carousel.label,
          // Toward inline-end (left in RTL) over photo subject
          position: { x: 52, y: 56 },
          maxItems: 4,
          previewTitles: seed.carousel.titles,
          stylePreset: "rail-soft",
          layoutPreset: "row-comfortable",
          productIds: [],
          categoryId: null,
        }
      : {
          enabled: false,
          categorySlug: "",
          categoryLabel: "",
          position: { x: 52, y: 56 },
          maxItems: 4,
          previewTitles: [],
          stylePreset: "rail-soft",
          layoutPreset: "row-comfortable",
          productIds: [],
          categoryId: null,
        },
  };
}

export function curatedSlidesFromDock(orbs: HeroOrbCategory[]): HeroSlideDraft[] {
  return CURATED_HERO_SEEDS.map((seed, i) => {
    const orb = orbs.find((o) => o.key === seed.orbKey);
    const config = configFromCuratedSeed(seed);
    if (orb) {
      config.background.imageUrl = orb.heroImage || seed.image;
    }
    return {
      id: `slide_${seed.orbKey}`,
      name: seed.name,
      sortOrder: i + 1,
      isActive: true,
      config,
    };
  });
}
