/**
 * Finalized L1 taxonomy — keep in sync with Storefront/src/config/final-l1-categories.ts.
 * تخفیف‌ها is dock-only (not an L1). Featured slots 1–4 after discounts @ 0.
 */

export const DISCOUNTS_ORB_KEY = "discounts";
/** Prefer plain catalog — storefront API has no discount sort key. */
export const DISCOUNTS_CATALOG_HREF = "/catalog";

export interface FinalL1Category {
  key: string;
  name: string;
  slug: string;
  iconSlug: string;
  heroImage: string;
  subtitle: string;
  ctaLabel: string;
  featuredOrder: number | null;
  aliases: string[];
}

export const DISCOUNTS_SPECIAL = {
  key: DISCOUNTS_ORB_KEY,
  name: "تخفیف‌ها",
  slug: "takhfif",
  iconSlug: "takhfif",
  heroImage: "/images/hero/hero-accessories-left.jpg",
  subtitle:
    "بهترین پیشنهادهای تخفیف‌دار ابزار صنعتی — قیمت‌های رقابتی برای تجهیز کارگاه",
  ctaLabel: "مشاهده تخفیف‌ها",
  featuredOrder: 0 as const,
  aliases: ["تخفیف‌ها", "تخفیف ها", "تخفیف"],
};

export const FINAL_L1_FEATURED_KEYS = [
  "metrology",
  "inserts",
  "workholding",
  "industrial-machines",
] as const;

/**
 * Canonical 12 L1 categories — merchandising order for mock + hero dock defaults.
 * Array order is the single FE display order (drills before toolholders).
 */
export const FINAL_L1_CATEGORIES: FinalL1Category[] = [
  {
    key: "metrology",
    name: "اندازه‌گیری",
    slug: "andaze-giri",
    iconSlug: "andaze-giri",
    heroImage: "/images/hero/hero-metrology-left.jpg",
    subtitle:
      "کولیس، میکرومتر و گیج‌های صنعتی — دقت قابل‌اعتماد برای کنترل کیفیت خط تولید",
    ctaLabel: "مشاهده اندازه‌گیری",
    featuredOrder: 1,
    aliases: [
      "اندازه‌گیری",
      "اندازه گیری",
      "ابزار اندازه‌گیری",
      "اندازه گیری دقیق",
      "اندازه‌گیری دقیق",
    ],
  },
  {
    key: "insert-tools",
    name: "ابزار اینسرتی",
    slug: "abzar-inserti",
    iconSlug: "abzar-inserti",
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle: "هلدر و سیستم‌های اینسرتی برای براده‌برداری پایدار و تعویض سریع",
    ctaLabel: "مشاهده ابزار اینسرتی",
    featuredOrder: null,
    aliases: ["ابزار اینسرتی", "اینسرتی"],
  },
  {
    key: "inserts",
    name: "اینسرت",
    slug: "insert",
    iconSlug: "insert",
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle: "اینسرت‌های کاربیدی و پوشش‌دار برای سطوح برش متنوع",
    ctaLabel: "مشاهده اینسرت",
    featuredOrder: 2,
    aliases: ["اینسرت"],
  },
  {
    key: "endmills",
    name: "فرز انگشتی",
    slug: "farz-angoshti",
    iconSlug: "farz-angoshti",
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle: "فرز انگشتی و ابزارهای پروفایل برای ماشین‌کاری دقیق قطعه",
    ctaLabel: "مشاهده فرز انگشتی",
    featuredOrder: null,
    aliases: ["فرز انگشتی", "ابزار انگشتی"],
  },
  {
    key: "taps",
    name: "قلاویز",
    slug: "ghalaviz",
    iconSlug: "ghalaviz",
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle: "قلاویز دستی و ماشینی برای رزوه‌کاری استاندارد صنعتی",
    ctaLabel: "مشاهده قلاویز",
    featuredOrder: null,
    aliases: ["قلاویز"],
  },
  {
    key: "drills",
    name: "مته‌ها",
    slug: "mete",
    iconSlug: "mete",
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle: "مته‌های HSS و کاربید برای سوراخ‌کاری تمیز و تکرارپذیر",
    ctaLabel: "مشاهده مته‌ها",
    featuredOrder: null,
    aliases: ["مته‌ها", "مته"],
  },
  {
    key: "toolholders",
    name: "ابزارگیر",
    slug: "abzar-gir",
    iconSlug: "abzar-gir",
    heroImage: "/images/hero/hero-holding-left.jpg",
    subtitle: "هولدر و رابط‌های ابزار برای پایداری بیشتر در اسپیندل",
    ctaLabel: "مشاهده ابزارگیر",
    featuredOrder: null,
    aliases: ["ابزارگیر", "ابزار گیر"],
  },
  {
    key: "workholding",
    name: "ابزار گیرشی",
    slug: "abzar-gireshi",
    iconSlug: "abzar-gireshi",
    heroImage: "/images/hero/hero-holding-left.jpg",
    subtitle: "گیره‌ها و سیستم‌های فیکسچر برای نگهداشت ایمن قطعه کار",
    ctaLabel: "مشاهده ابزار گیرشی",
    featuredOrder: 3,
    aliases: ["ابزار گیرشی"],
  },
  {
    key: "industrial-machines",
    name: "دستگاه‌های صنعتی",
    slug: "dastgah-sanati",
    iconSlug: "dastgah-sanati",
    heroImage: "/images/hero/hero-machines-left.jpg",
    subtitle: "ماشین‌ها و تجهیزات صنعتی برای تجهیز کارگاه و خط تولید",
    ctaLabel: "مشاهده دستگاه‌ها",
    featuredOrder: 4,
    aliases: ["دستگاه‌های صنعتی", "دستگاه های صنعتی"],
  },
  {
    key: "heli-coil",
    name: "هلی کویل",
    slug: "heli-coil",
    iconSlug: "heli-coil",
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle: "فنر، قلاویز و کیت‌های هلی‌کویل برای ترمیم رزوه",
    ctaLabel: "مشاهده هلی کویل",
    featuredOrder: null,
    aliases: ["هلی کویل", "هلی‌کویل"],
  },
  {
    key: "workshop-tools",
    name: "ابزار کارگاهی",
    slug: "abzar-kargahi",
    iconSlug: "abzar-kargahi",
    heroImage: "/images/hero/hero-holding-left.jpg",
    subtitle: "ابزار کارگاهی برای کار روزمره کارگاه",
    ctaLabel: "مشاهده ابزار کارگاهی",
    featuredOrder: null,
    aliases: ["ابزار کارگاهی"],
  },
  {
    key: "lubricants",
    name: "روغن و روانکار",
    slug: "roghan-ravankar",
    iconSlug: "roghan-ravankar",
    heroImage: "/images/hero/hero-accessories-left.jpg",
    subtitle: "روغن برش و روانکار صنعتی برای طول عمر ابزار و کیفیت سطح",
    ctaLabel: "مشاهده روغن و روانکار",
    featuredOrder: null,
    aliases: ["روغن و روانکار", "روغن و زوانکار", "لوازم جانبی صنعتی"],
  },
];

export const FINAL_L1_NAMES = FINAL_L1_CATEGORIES.map((c) => c.name);

/**
 * Stable mock DB ids for the 12 L1 roots (1–12).
 * Fixed by key — do not derive from array index so merchandising reorder
 * does not break mock parent_id links.
 */
export const FINAL_L1_MOCK_IDS: Record<string, number> = {
  metrology: 1,
  "insert-tools": 2,
  inserts: 3,
  endmills: 4,
  taps: 5,
  toolholders: 6,
  workholding: 7,
  "industrial-machines": 8,
  "heli-coil": 9,
  drills: 10,
  "workshop-tools": 11,
  lubricants: 12,
};
