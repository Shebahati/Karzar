/**
 * Curated hero pack — تخفیف‌ها + all 12 finalized L1 categories.
 * Each seed is hand-varied (overlay / type / CTA / badge / carousel / animation).
 */

import type {
  DsButtonSize,
  DsButtonStyle,
  DsCarouselLayout,
  DsCarouselStyle,
  HeroAnimationPreset,
  HeroBadgeKind,
  HeroBadgeStyle,
  HeroBuilderConfig,
  HeroOrbCategory,
  HeroSlideDraft,
  MobileComposePreset,
  TextAlign,
} from "./types";
import { DISCOUNTS_CATALOG_HREF, DISCOUNTS_ORB_KEY } from "@/config/final-l1-categories";
import { buttonStyleCss } from "./presets";

function createId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 9)}`;
}

type CtaSeed = {
  label: string;
  href: string;
  stylePreset: DsButtonStyle;
  sizePreset: DsButtonSize;
  position: { x: number; y: number };
};

type SlideSeed = {
  orbKey: string;
  name: string;
  title: string;
  subtitle: string;
  image: string;
  focal: string;
  animation: HeroAnimationPreset;
  minHeight: number;
  mobilePreset: MobileComposePreset;
  overlay: {
    gradientFrom: string;
    gradientTo: string;
    gradientAngle: number;
    opacity?: number;
  };
  typography: {
    position: { x: number; y: number };
    maxWidth: number;
    titleSize: number;
    subtitleSize: number;
    align: TextAlign;
  };
  ctaPrimary: CtaSeed;
  ctaSecondary?: CtaSeed;
  badges: Array<{
    label: string;
    meta: string;
    kind: HeroBadgeKind;
    style: HeroBadgeStyle;
    position: { x: number; y: number };
    animated: boolean;
  }>;
  carousel?: {
    label: string;
    titles: string[];
    hrefSlug?: string;
    stylePreset: DsCarouselStyle;
    layoutPreset: DsCarouselLayout;
    position: { x: number; y: number };
    maxItems: number;
  };
};

/** Thirteen distinct power slides — discounts + every L1 (not clones). */
export const CURATED_HERO_SEEDS: SlideSeed[] = [
  {
    orbKey: DISCOUNTS_ORB_KEY,
    name: "تخفیف‌ها",
    title: "تخفیف‌های ویژه کارزار",
    subtitle:
      "پیشنهادهای پرتخفیف ابزار صنعتی — قیمت رقابتی برای تجهیز کارگاه و خط تولید",
    image: "/images/hero/hero-accessories-left.jpg",
    focal: "left 38%",
    animation: "float",
    minHeight: 760,
    mobilePreset: "copy-focus",
    overlay: {
      gradientFrom: "rgba(80,8,12,0.15)",
      gradientTo: "rgba(12,8,8,0.92)",
      gradientAngle: 105,
      opacity: 1,
    },
    typography: {
      position: { x: 6, y: 22 },
      maxWidth: 420,
      titleSize: 46,
      subtitleSize: 15,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده تخفیف‌ها",
      href: DISCOUNTS_CATALOG_HREF,
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 56 },
    },
    ctaSecondary: {
      label: "کاتالوگ کامل",
      href: "/catalog",
      stylePreset: "on-dark-outline",
      sizePreset: "md",
      position: { x: 6, y: 68 },
    },
    badges: [
      {
        label: "پرتخفیف",
        meta: "تا ۲۵٪",
        kind: "discount",
        style: "ribbon",
        position: { x: 6, y: 12 },
        animated: true,
      },
      {
        label: "محدود زمانی",
        meta: "این هفته",
        kind: "flash_sale",
        style: "stamp",
        position: { x: 28, y: 12 },
        animated: false,
      },
    ],
  },
  {
    orbKey: "metrology",
    name: "اندازه‌گیری",
    title: "اندازه‌گیری دقیق",
    subtitle:
      "کولیس، میکرومتر و گیج‌های صنعتی از برندهای معتبر — کنترل کیفیت مطمئن برای خط تولید شما",
    image: "/images/hero/hero-metrology-left.jpg",
    focal: "left 42%",
    animation: "fade-up",
    minHeight: 720,
    mobilePreset: "balanced",
    overlay: {
      gradientFrom: "rgba(12,12,12,0.06)",
      gradientTo: "rgba(12,12,12,0.84)",
      gradientAngle: 90,
    },
    typography: {
      position: { x: 5, y: 24 },
      maxWidth: 440,
      titleSize: 42,
      subtitleSize: 16,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده اندازه‌گیری",
      href: "/categories/andaze-giri",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 5, y: 54 },
    },
    ctaSecondary: {
      label: "استعلام قیمت",
      href: "/quote",
      stylePreset: "on-dark-glass",
      sizePreset: "md",
      position: { x: 5, y: 66 },
    },
    badges: [
      {
        label: "اصالت کالا",
        meta: "گارانتی",
        kind: "trust",
        style: "chip",
        position: { x: 5, y: 14 },
        animated: true,
      },
    ],
    carousel: {
      label: "منتخب مترولوژی",
      titles: ["کولیس دیجیتال", "میکرومتر بیرونی", "ساعت اندیکاتور", "بلوک سنجه"],
      hrefSlug: "andaze-giri",
      stylePreset: "rail-soft",
      layoutPreset: "row-comfortable",
      position: { x: 52, y: 54 },
      maxItems: 4,
    },
  },
  {
    orbKey: "insert-tools",
    name: "ابزار اینسرتی",
    title: "ابزار اینسرتی پایدار",
    subtitle: "هلدر و سیستم‌های اینسرتی برای براده‌برداری پایدار و تعویض سریع",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "left 48%",
    animation: "slide-in",
    minHeight: 710,
    mobilePreset: "media-focus",
    overlay: {
      gradientFrom: "rgba(12,12,12,0.2)",
      gradientTo: "rgba(12,12,12,0.8)",
      gradientAngle: 108,
      opacity: 0.96,
    },
    typography: {
      position: { x: 6, y: 28 },
      maxWidth: 400,
      titleSize: 40,
      subtitleSize: 15,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده ابزار اینسرتی",
      href: "/categories/abzar-inserti",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 6, y: 58 },
    },
    ctaSecondary: {
      label: "استعلام موجودی",
      href: "/quote",
      stylePreset: "on-dark-outline",
      sizePreset: "md",
      position: { x: 6, y: 70 },
    },
    badges: [
      {
        label: "براده‌برداری",
        meta: "هلدر",
        kind: "new_arrival",
        style: "ribbon",
        position: { x: 6, y: 15 },
        animated: true,
      },
    ],
  },
  {
    orbKey: "inserts",
    name: "اینسرت",
    title: "اینسرت کاربیدی",
    subtitle:
      "اینسرت‌های پوشش‌دار برای سطوح برش متنوع — تعویض سریع، عمر طولانی، کیفیت ثابت",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "center left",
    animation: "zoom-soft",
    minHeight: 700,
    mobilePreset: "media-focus",
    overlay: {
      gradientFrom: "rgba(20,10,8,0.12)",
      gradientTo: "rgba(8,8,10,0.88)",
      gradientAngle: 78,
    },
    typography: {
      position: { x: 4, y: 30 },
      maxWidth: 400,
      titleSize: 40,
      subtitleSize: 15,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده اینسرت",
      href: "/categories/insert",
      stylePreset: "primary",
      sizePreset: "pill",
      position: { x: 4, y: 58 },
    },
    ctaSecondary: {
      label: "هلدر اینسرتی",
      href: "/categories/abzar-inserti",
      stylePreset: "soft",
      sizePreset: "sm",
      position: { x: 22, y: 58 },
    },
    badges: [
      {
        label: "انتخاب صنعتی",
        meta: "CVD / PVD",
        kind: "campaign",
        style: "pill",
        position: { x: 4, y: 18 },
        animated: true,
      },
    ],
    carousel: {
      label: "پرفروش اینسرت",
      titles: ["CNMG 120408", "DCMT 11T304", "VNMG 160408", "APKT 1604"],
      hrefSlug: "insert",
      stylePreset: "cards-elevated",
      layoutPreset: "row-compact",
      position: { x: 48, y: 58 },
      maxItems: 4,
    },
  },
  {
    orbKey: "endmills",
    name: "فرز انگشتی",
    title: "فرز انگشتی دقیق",
    subtitle:
      "ابزارهای پروفایل و فرز انگشتی برای ماشین‌کاری تمیز — از کاربید تا پوشش‌های پیشرفته",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "left 44%",
    animation: "stagger-up",
    minHeight: 720,
    mobilePreset: "balanced",
    overlay: {
      gradientFrom: "rgba(12,12,12,0.04)",
      gradientTo: "rgba(12,12,12,0.9)",
      gradientAngle: 92,
      opacity: 0.98,
    },
    typography: {
      position: { x: 5, y: 26 },
      maxWidth: 460,
      titleSize: 42,
      subtitleSize: 16,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده فرز انگشتی",
      href: "/categories/farz-angoshti",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 5, y: 58 },
    },
    ctaSecondary: {
      label: "استعلام موجودی",
      href: "/quote",
      stylePreset: "on-dark-glass",
      sizePreset: "md",
      position: { x: 22, y: 58 },
    },
    badges: [
      {
        label: "ماشین‌کاری",
        meta: "۴۹۱",
        kind: "campaign",
        style: "pill",
        position: { x: 5, y: 14 },
        animated: true,
      },
    ],
  },
  {
    orbKey: "taps",
    name: "قلاویز",
    title: "قلاویز صنعتی",
    subtitle: "قلاویز دستی و ماشینی برای رزوه‌کاری استاندارد صنعتی",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "left 36%",
    animation: "fade-in",
    minHeight: 690,
    mobilePreset: "dock-first",
    overlay: {
      gradientFrom: "rgba(12,18,28,0.22)",
      gradientTo: "rgba(12,12,12,0.84)",
      gradientAngle: 118,
      opacity: 0.94,
    },
    typography: {
      position: { x: 8, y: 30 },
      maxWidth: 360,
      titleSize: 38,
      subtitleSize: 15,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده قلاویز",
      href: "/categories/ghalaviz",
      stylePreset: "soft",
      sizePreset: "lg",
      position: { x: 8, y: 60 },
    },
    ctaSecondary: {
      label: "کاتالوگ",
      href: "/catalog",
      stylePreset: "on-dark-outline",
      sizePreset: "md",
      position: { x: 8, y: 72 },
    },
    badges: [],
  },
  {
    orbKey: "toolholders",
    name: "ابزار گیر",
    title: "ابزارگیر دقیق",
    subtitle: "هولدر و رابط‌های ابزار برای پایداری بیشتر در اسپیندل",
    image: "/images/hero/hero-holding-left.jpg",
    focal: "left 50%",
    animation: "float",
    minHeight: 730,
    mobilePreset: "media-focus",
    overlay: {
      gradientFrom: "rgba(12,12,12,0.28)",
      gradientTo: "rgba(12,12,12,0.76)",
      gradientAngle: 68,
    },
    typography: {
      position: { x: 5, y: 18 },
      maxWidth: 400,
      titleSize: 40,
      subtitleSize: 15,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده ابزار گیر",
      href: "/categories/abzar-gir",
      stylePreset: "primary",
      sizePreset: "md",
      position: { x: 5, y: 52 },
    },
    ctaSecondary: {
      label: "استعلام",
      href: "/quote",
      stylePreset: "on-dark-glass",
      sizePreset: "sm",
      position: { x: 5, y: 63 },
    },
    badges: [
      {
        label: "پایداری اسپیندل",
        meta: "هولدر",
        kind: "trust",
        style: "banner",
        position: { x: 5, y: 10 },
        animated: false,
      },
    ],
  },
  {
    orbKey: "workholding",
    name: "ابزار گیرشی",
    title: "ثابت‌کاری حرفه‌ای",
    subtitle:
      "گیره، فیکسچر و سیستم‌های نگه‌دارنده — ثبات بیشتر، لرزش کمتر، نتیجه تمیزتر",
    image: "/images/hero/hero-holding-left.jpg",
    focal: "left 48%",
    animation: "slide-in",
    minHeight: 740,
    mobilePreset: "dock-first",
    overlay: {
      gradientFrom: "rgba(12,16,22,0.1)",
      gradientTo: "rgba(8,10,14,0.9)",
      gradientAngle: 95,
    },
    typography: {
      position: { x: 8, y: 28 },
      maxWidth: 480,
      titleSize: 44,
      subtitleSize: 16,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده ابزار گیرشی",
      href: "/categories/abzar-gireshi",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 8, y: 58 },
    },
    ctaSecondary: {
      label: "مشاوره فنی",
      href: "/quote",
      stylePreset: "on-dark-outline",
      sizePreset: "md",
      position: { x: 8, y: 70 },
    },
    badges: [
      {
        label: "ارسال رایگان",
        meta: "تهران",
        kind: "free_shipping",
        style: "banner",
        position: { x: 8, y: 16 },
        animated: false,
      },
    ],
    carousel: {
      label: "فیکسچر منتخب",
      titles: ["گیره ماشین", "پلیت گیرشی", "کلمپ هیدرولیک"],
      hrefSlug: "abzar-gireshi",
      stylePreset: "strip-minimal",
      layoutPreset: "row-large",
      position: { x: 55, y: 62 },
      maxItems: 3,
    },
  },
  {
    orbKey: "industrial-machines",
    name: "دستگاه‌های صنعتی",
    title: "ظرفیت کارگاه را بالا ببرید",
    subtitle:
      "ماشین‌ها و تجهیزات صنعتی برای ارتقای خط تولید — انتخاب تخصصی با پشتیبانی کارزار",
    image: "/images/hero/hero-machines-left.jpg",
    focal: "left 35%",
    animation: "stagger-up",
    minHeight: 780,
    mobilePreset: "media-focus",
    overlay: {
      gradientFrom: "rgba(8,12,20,0.2)",
      gradientTo: "rgba(4,6,12,0.94)",
      gradientAngle: 112,
    },
    typography: {
      position: { x: 5, y: 20 },
      maxWidth: 500,
      titleSize: 48,
      subtitleSize: 17,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده دستگاه‌ها",
      href: "/categories/dastgah-sanati",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 5, y: 52 },
    },
    ctaSecondary: {
      label: "درخواست مشاوره",
      href: "/quote",
      stylePreset: "on-dark-glass",
      sizePreset: "pill",
      position: { x: 5, y: 64 },
    },
    badges: [
      {
        label: "تجهیز کارگاه",
        meta: "صنعتی",
        kind: "new_arrival",
        style: "pill",
        position: { x: 5, y: 10 },
        animated: true,
      },
      {
        label: "پشتیبانی فنی",
        meta: "کارزار",
        kind: "trust",
        style: "chip",
        position: { x: 26, y: 10 },
        animated: false,
      },
    ],
    carousel: {
      label: "ماشین‌ابزار",
      titles: ["تراش CNC", "فرز عمودی", "دریل ستونی", "اره نواری"],
      hrefSlug: "dastgah-sanati",
      stylePreset: "spotlight",
      layoutPreset: "row-comfortable",
      position: { x: 50, y: 52 },
      maxItems: 4,
    },
  },
  {
    orbKey: "heli-coil",
    name: "هلی کویل",
    title: "ترمیم رزوه هلی‌کویل",
    subtitle: "فنر، قلاویز و کیت‌های هلی‌کویل برای ترمیم رزوه",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "right 42%",
    animation: "fade-up",
    minHeight: 700,
    mobilePreset: "copy-focus",
    overlay: {
      gradientFrom: "rgba(40,18,12,0.24)",
      gradientTo: "rgba(12,12,12,0.8)",
      gradientAngle: 122,
      opacity: 0.95,
    },
    typography: {
      position: { x: 7, y: 32 },
      maxWidth: 340,
      titleSize: 36,
      subtitleSize: 14,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده هلی کویل",
      href: "/categories/heli-coil",
      stylePreset: "primary",
      sizePreset: "md",
      position: { x: 7, y: 58 },
    },
    ctaSecondary: {
      label: "استعلام",
      href: "/quote",
      stylePreset: "on-dark-glass",
      sizePreset: "sm",
      position: { x: 7, y: 69 },
    },
    badges: [
      {
        label: "ترمیم رزوه",
        meta: "کیت",
        kind: "limited",
        style: "ribbon",
        position: { x: 7, y: 18 },
        animated: true,
      },
    ],
  },
  {
    orbKey: "drills",
    name: "مته",
    title: "مته‌های صنعتی",
    subtitle: "مته‌های HSS و کاربید برای سوراخ‌کاری تمیز و تکرارپذیر",
    image: "/images/hero/hero-cutting-left.jpg",
    focal: "left 46%",
    animation: "zoom-soft",
    minHeight: 720,
    mobilePreset: "balanced",
    overlay: {
      gradientFrom: "rgba(12,12,12,0.12)",
      gradientTo: "rgba(12,12,12,0.88)",
      gradientAngle: 84,
    },
    typography: {
      position: { x: 5, y: 24 },
      maxWidth: 420,
      titleSize: 42,
      subtitleSize: 15,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده مته",
      href: "/categories/mete",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 5, y: 54 },
    },
    ctaSecondary: {
      label: "کاتالوگ",
      href: "/catalog",
      stylePreset: "on-dark-glass",
      sizePreset: "md",
      position: { x: 5, y: 66 },
    },
    badges: [
      {
        label: "سوراخ‌کاری",
        meta: "HSS",
        kind: "campaign",
        style: "chip",
        position: { x: 5, y: 13 },
        animated: true,
      },
    ],
    carousel: {
      label: "مته‌های منتخب",
      titles: ["مته کبالت", "مته کاربید", "مته مرکز", "مته پله‌ای"],
      hrefSlug: "mete",
      stylePreset: "rail-soft",
      layoutPreset: "row-comfortable",
      position: { x: 51, y: 56 },
      maxItems: 4,
    },
  },
  {
    orbKey: "workshop-tools",
    name: "ابزار کارگاهی : دریل عادی",
    title: "ابزار کارگاهی",
    subtitle: "ابزار کارگاهی و دریل عادی برای کار روزمره کارگاه",
    image: "/images/hero/hero-holding-left.jpg",
    focal: "left 55%",
    animation: "fade-in",
    minHeight: 700,
    mobilePreset: "dock-first",
    overlay: {
      gradientFrom: "rgba(12,12,12,0.32)",
      gradientTo: "rgba(12,12,12,0.74)",
      gradientAngle: 62,
      opacity: 0.92,
    },
    typography: {
      position: { x: 5, y: 28 },
      maxWidth: 380,
      titleSize: 38,
      subtitleSize: 15,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده ابزار کارگاهی",
      href: "/categories/abzar-kargahi",
      stylePreset: "soft",
      sizePreset: "lg",
      position: { x: 5, y: 58 },
    },
    ctaSecondary: {
      label: "استعلام قیمت",
      href: "/quote",
      stylePreset: "on-dark-outline",
      sizePreset: "md",
      position: { x: 5, y: 70 },
    },
    badges: [
      {
        label: "کارگاه",
        meta: "روزمره",
        kind: "free_shipping",
        style: "pill",
        position: { x: 5, y: 16 },
        animated: false,
      },
    ],
  },
  {
    orbKey: "lubricants",
    name: "روغن و روانکار",
    title: "روغن و روانکار",
    subtitle: "روغن برش و روانکار صنعتی برای طول عمر ابزار و کیفیت سطح",
    image: "/images/hero/hero-accessories-left.jpg",
    focal: "left 40%",
    animation: "float",
    minHeight: 720,
    mobilePreset: "copy-focus",
    overlay: {
      gradientFrom: "rgba(22,28,18,0.16)",
      gradientTo: "rgba(10,12,10,0.9)",
      gradientAngle: 96,
    },
    typography: {
      position: { x: 5, y: 26 },
      maxWidth: 440,
      titleSize: 40,
      subtitleSize: 16,
      align: "start",
    },
    ctaPrimary: {
      label: "مشاهده روغن و روانکار",
      href: "/categories/roghan-ravankar",
      stylePreset: "primary",
      sizePreset: "lg",
      position: { x: 5, y: 56 },
    },
    ctaSecondary: {
      label: "کاتالوگ",
      href: "/catalog",
      stylePreset: "on-dark-glass",
      sizePreset: "md",
      position: { x: 5, y: 68 },
    },
    badges: [
      {
        label: "عمر ابزار",
        meta: "برش",
        kind: "flash_sale",
        style: "chip",
        position: { x: 5, y: 14 },
        animated: true,
      },
    ],
  },
];

function buttonFromCta(cta: CtaSeed) {
  const css = buttonStyleCss(cta.stylePreset);
  return {
    id: createId("btn"),
    label: cta.label,
    variant:
      cta.stylePreset === "on-dark-outline"
        ? ("outline" as const)
        : cta.stylePreset === "on-dark-glass"
          ? ("glass" as const)
          : ("solid" as const),
    bgColor: css.background,
    textColor: css.color,
    borderRadius: cta.sizePreset === "pill" ? 999 : 12,
    position: cta.position,
    action: { type: "href" as const, value: cta.href },
    stylePreset: cta.stylePreset,
    sizePreset: cta.sizePreset,
  };
}

/** Build one responsive RTL-safe slide config from a seed. */
export function configFromCuratedSeed(seed: SlideSeed): HeroBuilderConfig {
  return {
    version: 1,
    minHeight: seed.minHeight,
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
      solidColor: "rgba(12,12,12,0.72)",
      gradientFrom: seed.overlay.gradientFrom,
      gradientTo: seed.overlay.gradientTo,
      gradientAngle: seed.overlay.gradientAngle,
      opacity: seed.overlay.opacity ?? 1,
    },
    typography: {
      title: seed.title,
      subtitle: seed.subtitle,
      titleColor: "#FFFFFF",
      subtitleColor: "rgba(255,255,255,0.9)",
      titleSize: seed.typography.titleSize,
      subtitleSize: seed.typography.subtitleSize,
      align: seed.typography.align,
      position: seed.typography.position,
      maxWidth: seed.typography.maxWidth,
    },
    buttons: [
      buttonFromCta(seed.ctaPrimary),
      ...(seed.ctaSecondary ? [buttonFromCta(seed.ctaSecondary)] : []),
    ],
    badges: seed.badges.map((b) => ({
      id: createId("badge"),
      kind: b.kind,
      style: b.style,
      label: b.label,
      meta: b.meta,
      position: b.position,
      animated: b.animated,
    })),
    carousel: seed.carousel
      ? {
          enabled: true,
          categorySlug: seed.carousel.hrefSlug ?? "",
          categoryLabel: seed.carousel.label,
          position: seed.carousel.position,
          maxItems: seed.carousel.maxItems,
          previewTitles: seed.carousel.titles,
          stylePreset: seed.carousel.stylePreset,
          layoutPreset: seed.carousel.layoutPreset,
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
      if (seed.orbKey === DISCOUNTS_ORB_KEY) {
        config.typography.title = seed.title;
        config.typography.subtitle = orb.subtitle || seed.subtitle;
      } else {
        config.typography.subtitle = orb.subtitle || seed.subtitle;
      }
    }
    return {
      id: `slide_${seed.orbKey}`,
      name: seed.name,
      sortOrder: i + 1,
      isActive: true,
      mobilePreset: seed.mobilePreset,
      config,
    };
  });
}
