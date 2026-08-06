/**
 * Finalized storefront L1 taxonomy — single source for mock tree + hero marketing.
 * Live API (USE_MOCK=false) may return other L1 names; marketing still matches by alias.
 * تخفیف‌ها is NOT an L1 — dock-only via DISCOUNTS_SPECIAL.
 */

export const DISCOUNTS_ORB_KEY = "discounts";
/**
 * Catalog entry for تخفیف‌ها dock / پرتخفیف‌ها CTA.
 * `on_sale=1` is an FE filter (see ProductListParams.on_sale) — not a live API sort key.
 */
export const DISCOUNTS_CATALOG_HREF = "/catalog?on_sale=1";

export interface FinalL1Category {
  /** Stable dock / marketing key */
  key: string;
  /** Exact Persian display name */
  name: string;
  slug: string;
  /** Key into CATEGORY_ICON_BY_SLUG */
  iconSlug: string;
  heroImage: string;
  subtitle: string;
  ctaLabel: string;
  /**
   * Featured dock order 1–4 (0 reserved for discounts).
   * null = overlay «همه محصولات» only.
   */
  featuredOrder: number | null;
  /** Match live DB names; first entry should be exact `name` */
  aliases: string[];
}

/** Dock-only special — never listed in «همه محصولات». */
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

/** RTL dock featured L1 keys (slots 1–4 after تخفیف‌ها @ 0). */
export const FINAL_L1_FEATURED_KEYS = [
  "metrology",
  "inserts",
  "workholding",
  "industrial-machines",
] as const;

/** Canonical 12 L1 categories — exact names for mock + menus. */
export const FINAL_L1_CATEGORIES: FinalL1Category[] = [
  {
    key: "metrology",
    name: "اندازه‌گیری",
    slug: "andaze-giri",
    iconSlug: "andaze-giri",
    heroImage: "/images/hero/hero-metrology-left.jpg",
    subtitle:
      "کولیس، میکرومتر و گیج‌های صنعتی از برندهای معتبر — کنترل کیفیت مطمئن برای خط تولید شما",
    ctaLabel: "مشاهده اندازه‌گیری",
    featuredOrder: 1,
    aliases: [
      "اندازه‌گیری",
      "اندازه گیری",
      "اندازه گیری دقیق",
      "اندازه‌گیری دقیق",
      "اندازه گیری آزمایشگاهی",
      "اندازه گیری فرز CNC",
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
    aliases: ["ابزار اینسرتی"],
  },
  {
    key: "inserts",
    name: "اینسرت",
    slug: "insert",
    iconSlug: "insert",
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle:
      "اینسرت‌های پوشش‌دار برای سطوح برش متنوع — تعویض سریع، عمر طولانی، کیفیت ثابت",
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
    subtitle:
      "ابزارهای پروفایل و فرز انگشتی برای ماشین‌کاری تمیز — از کاربید تا پوشش‌های پیشرفته",
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
    key: "toolholders",
    name: "ابزار گیر",
    slug: "abzar-gir",
    iconSlug: "abzar-gir",
    heroImage: "/images/hero/hero-holding-left.jpg",
    subtitle: "هولدر و رابط‌های ابزار برای پایداری بیشتر در اسپیندل",
    ctaLabel: "مشاهده ابزار گیر",
    featuredOrder: null,
    aliases: ["ابزار گیر", "ابزارگیر"],
  },
  {
    key: "workholding",
    name: "ابزار گیرشی",
    slug: "abzar-gireshi",
    iconSlug: "abzar-gireshi",
    heroImage: "/images/hero/hero-holding-left.jpg",
    subtitle:
      "گیره، فیکسچر و سیستم‌های نگه‌دارنده — ثبات بیشتر، لرزش کمتر، نتیجه تمیزتر در ماشین‌کاری",
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
    subtitle:
      "ماشین‌ها و تجهیزات صنعتی برای ارتقای ظرفیت کارگاه — انتخاب تخصصی، پشتیبانی کارزاری",
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
    key: "drills",
    name: "مته",
    slug: "mete",
    iconSlug: "mete",
    heroImage: "/images/hero/hero-cutting-left.jpg",
    subtitle: "مته‌های HSS و کاربید برای سوراخ‌کاری تمیز و تکرارپذیر",
    ctaLabel: "مشاهده مته",
    featuredOrder: null,
    aliases: ["مته"],
  },
  {
    key: "workshop-tools",
    name: "ابزار کارگاهی : دریل عادی",
    slug: "abzar-kargahi",
    iconSlug: "abzar-kargahi",
    heroImage: "/images/hero/hero-holding-left.jpg",
    subtitle: "ابزار کارگاهی و دریل عادی برای کار روزمره کارگاه",
    ctaLabel: "مشاهده ابزار کارگاهی",
    featuredOrder: null,
    aliases: ["ابزار کارگاهی : دریل عادی", "ابزار کارگاهی"],
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

/** Stable mock DB ids for the 12 L1 roots (1–12). */
export const FINAL_L1_MOCK_IDS: Record<string, number> = Object.fromEntries(
  FINAL_L1_CATEGORIES.map((c, i) => [c.key, i + 1]),
);
