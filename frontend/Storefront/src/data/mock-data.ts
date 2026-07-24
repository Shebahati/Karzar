/**
 * In-memory seed data for the storefront mock layer.
 *
 * Shapes here are the single source of truth for `API_REQUIREMENTS_STOREFRONT.txt`.
 * Categories form a strict 3-layer tree (depth 1 → 2 → 3); only depth-3 leaf
 * nodes carry products, mirroring the admin "Ultimate Product Entry Form" rule.
 */

import type { Brand, Category } from "@/types/category";
import type { ProductDetail, ProductSummary } from "@/types/product";
import type { Article, BlogPost, HeroSlide, ProductComment } from "@/types/content";
import { VERNIER_CALIPER_ARTICLE } from "@/data/articles/how-to-read-vernier-caliper";
import {
  expandCategories,
  expandCategoryIcons,
  expandProducts,
} from "./mock-catalog-generator";

const IMG = (seed: string) =>
  `https://picsum.photos/seed/${seed}/800/800`;

/* -------------------------------------------------------------------------- */
/*  Categories (flat list with parent_id; tree is derived).                   */
/* -------------------------------------------------------------------------- */
const BASE_CATEGORIES: Category[] = [
  // Layer 1
  { id: 1, name: "ابزار برقی", parent_id: null },
  { id: 2, name: "ابزار دستی", parent_id: null },
  { id: 3, name: "ابزار اندازه‌گیری", parent_id: null },
  { id: 4, name: "تجهیزات کارگاهی", parent_id: null },

  // Layer 2 — under ابزار برقی
  { id: 10, name: "دریل و دریل شارژی", parent_id: 1 },
  { id: 11, name: "فرز و سنگ", parent_id: 1 },
  // Layer 2 — under ابزار دستی
  { id: 20, name: "آچار", parent_id: 2 },
  { id: 21, name: "انبر و گیره", parent_id: 2 },
  // Layer 2 — under ابزار اندازه‌گیری
  { id: 30, name: "کولیس و میکرومتر", parent_id: 3 },
  // Layer 2 — under تجهیزات کارگاهی
  { id: 40, name: "میز و گیره کارگاهی", parent_id: 4 },

  // Layer 3 (leaf, selectable) — under دریل
  { id: 100, name: "دریل چکشی", parent_id: 10 },
  { id: 101, name: "دریل شارژی", parent_id: 10 },
  // Layer 3 — under فرز
  { id: 110, name: "مینی فرز", parent_id: 11 },
  { id: 111, name: "فرز انگشتی", parent_id: 11 },
  // Layer 3 — under آچار
  { id: 200, name: "آچار فرانسه", parent_id: 20 },
  { id: 201, name: "آچار رینگی", parent_id: 20 },
  // Layer 3 — under انبر و گیره
  { id: 210, name: "گیره مکانیک", parent_id: 21 },
  { id: 211, name: "انبردست", parent_id: 21 },
  // Layer 3 — under کولیس
  { id: 300, name: "کولیس دیجیتال", parent_id: 30 },
  { id: 301, name: "میکرومتر", parent_id: 30 },
  // Layer 3 — under میز کارگاهی
  { id: 400, name: "گیره رومیزی", parent_id: 40 },
];

export const CATEGORIES = expandCategories(BASE_CATEGORIES);

const BASE_CATEGORY_ICONS: Record<number, string> = {
  1: "Activity",
  2: "Setting",
  3: "Filter2",
  4: "Work",
};

export const CATEGORY_ICONS = expandCategoryIcons(BASE_CATEGORY_ICONS, CATEGORIES);

/* -------------------------------------------------------------------------- */
/*  Brands.                                                                    */
/* -------------------------------------------------------------------------- */
export const BRANDS: Brand[] = [
  { id: 1, name: "بوش", country: "آلمان", product_count: 4 },
  { id: 2, name: "ماکیتا", country: "ژاپن", product_count: 3 },
  { id: 3, name: "رونیکس", country: "ایران", product_count: 2 },
  { id: 4, name: "میتوتویو", country: "ژاپن", product_count: 2 },
  { id: 5, name: "استنلی", country: "آمریکا", product_count: 1 },
];

/* -------------------------------------------------------------------------- */
/*  Products.                                                                  */
/* -------------------------------------------------------------------------- */
type RawProduct = Omit<ProductDetail, "category" | "brand" | "stock_status"> & {
  category_id: number;
  brand_id: number | null;
};

const BASE_PRODUCTS: RawProduct[] = [
  {
    id: 1,
    sku: "BSH-GSB-13RE",
    name: "دریل چکشی بوش مدل GSB 13 RE",
    category_id: 100,
    brand_id: 1,
    base_price: "4850000",
    original_price: "5400000",
    discount_percent: 10,
    stock_quantity: "18",
    stock_unit: "piece",
    low_stock: false,
    availability: true,
    warranty_text: "۱۸ ماه گارانتی شرکتی",
    weight_grams: "1800",
    is_original: true,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("drill-bosch"),
    images: [
      { id: 1, url: IMG("drill-bosch"), is_primary: true },
      { id: 2, url: IMG("drill-bosch-2"), is_primary: false },
      { id: 3, url: IMG("drill-bosch-3"), is_primary: false },
    ],
    description:
      "دریل چکشی بوش GSB 13 RE با موتور قدرتمند ۶۰۰ وات، مناسب سوراخ‌کاری بتن، فلز و چوب. دارای کلاچ تنظیم دور و قابلیت چپ‌گرد و راست‌گرد.",
    specifications: {
      technical_specs: [
        { key: "توان موتور", value: "۶۰۰ وات" },
        { key: "حداکثر دور موتور", value: "۲۸۰۰ دور بر دقیقه" },
        { key: "ولتاژ", value: "۲۲۰ ولت" },
      ],
      dimensions: [
        { key: "طول", value: "۲۸۰" },
        { key: "وزن خالص", value: "۱۸۰۰" },
      ],
      features: {
        "چپ‌گرد و راست‌گرد": true,
        "قابلیت ضربه": true,
        "تنظیم دور": true,
        "چراغ LED": false,
      },
    },
    created_at: "2026-01-10T09:00:00Z",
    updated_at: "2026-06-01T09:00:00Z",
  },
  {
    id: 2,
    sku: "MKT-DDF485",
    name: "دریل شارژی ماکیتا مدل DDF485",
    category_id: 101,
    brand_id: 2,
    base_price: null,
    original_price: null,
    discount_percent: null,
    stock_quantity: "6",
    stock_unit: "piece",
    low_stock: true,
    availability: true,
    warranty_text: "۱۲ ماه گارانتی",
    weight_grams: "1600",
    is_original: true,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("drill-makita"),
    images: [
      { id: 4, url: IMG("drill-makita"), is_primary: true },
      { id: 5, url: IMG("drill-makita-2"), is_primary: false },
    ],
    description:
      "دریل/پیچ‌گوشتی شارژی ماکیتا ۱۸ ولت با موتور براشلس و گشتاور بالا. مناسب کاربری حرفه‌ای و مداوم.",
    specifications: {
      technical_specs: [
        { key: "ولتاژ باتری", value: "۱۸ ولت" },
        { key: "حداکثر گشتاور", value: "۵۰ نیوتن‌متر" },
        { key: "نوع موتور", value: "براشلس" },
      ],
      dimensions: [
        { key: "طول", value: "۱۷۲" },
        { key: "وزن خالص", value: "۱۶۰۰" },
      ],
      features: {
        براشلس: true,
        "چراغ LED": true,
        "دو سرعته": true,
      },
    },
    created_at: "2026-02-12T09:00:00Z",
    updated_at: "2026-06-10T09:00:00Z",
  },
  {
    id: 3,
    sku: "RNX-3110",
    name: "مینی فرز رونیکس مدل 3110",
    category_id: 110,
    brand_id: 3,
    base_price: "2150000",
    original_price: null,
    discount_percent: null,
    stock_quantity: "32",
    stock_unit: "piece",
    low_stock: false,
    availability: true,
    warranty_text: "۱۲ ماه گارانتی رونیکس",
    weight_grams: "2200",
    is_original: true,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("grinder-ronix"),
    images: [{ id: 6, url: IMG("grinder-ronix"), is_primary: true }],
    description:
      "مینی فرز رونیکس با صفحه ۱۸۰ میلی‌متری و موتور پرقدرت، مناسب برش و سنگ‌زنی فلزات.",
    specifications: {
      technical_specs: [
        { key: "توان موتور", value: "۲۰۰۰ وات" },
        { key: "قطر صفحه", value: "۱۸۰ میلی‌متر" },
      ],
      dimensions: [{ key: "وزن خالص", value: "۲۲۰۰" }],
      features: {
        "دسته جانبی": true,
        "محافظ صفحه": true,
      },
    },
    created_at: "2026-03-01T09:00:00Z",
    updated_at: "2026-06-12T09:00:00Z",
  },
  {
    id: 4,
    sku: "BSH-GWS-900",
    name: "فرز انگشتی بوش مدل GWS 900",
    category_id: 111,
    brand_id: 1,
    base_price: "3100000",
    original_price: "3650000",
    discount_percent: 15,
    stock_quantity: "12",
    stock_unit: "piece",
    low_stock: false,
    availability: true,
    warranty_text: "۱۸ ماه گارانتی شرکتی",
    weight_grams: "2000",
    is_original: true,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("die-grinder"),
    images: [{ id: 7, url: IMG("die-grinder"), is_primary: true }],
    description: "فرز انگشتی بوش با کنترل دور و بدنه ارگونومیک.",
    specifications: {
      technical_specs: [
        { key: "توان موتور", value: "۹۰۰ وات" },
        { key: "قطر صفحه", value: "۱۲۵ میلی‌متر" },
      ],
      dimensions: [{ key: "وزن خالص", value: "۲۰۰۰" }],
      features: { "کنترل دور": true },
    },
    created_at: "2026-03-15T09:00:00Z",
    updated_at: "2026-06-14T09:00:00Z",
  },
  {
    id: 5,
    sku: "STN-FR-250",
    name: "آچار فرانسه استنلی ۲۵۰ میلی‌متر",
    category_id: 200,
    brand_id: 5,
    base_price: "780000",
    original_price: null,
    discount_percent: null,
    stock_quantity: "45",
    stock_unit: "piece",
    low_stock: false,
    availability: true,
    warranty_text: "ضمانت اصالت کالا",
    weight_grams: "650",
    is_original: true,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("wrench-stanley"),
    images: [{ id: 8, url: IMG("wrench-stanley"), is_primary: true }],
    description: "آچار فرانسه استنلی از جنس فولاد کروم‌وانادیوم با فک متحرک نرم.",
    specifications: {
      technical_specs: [
        { key: "جنس", value: "کروم وانادیوم" },
        { key: "بازشو فک", value: "۳۰ میلی‌متر" },
      ],
      dimensions: [
        { key: "طول", value: "۲۵۰" },
        { key: "وزن خالص", value: "۶۵۰" },
      ],
      features: { "فک نرم‌کار": true },
    },
    created_at: "2026-01-20T09:00:00Z",
    updated_at: "2026-05-20T09:00:00Z",
  },
  {
    id: 6,
    sku: "RNX-RH-110",
    name: "آچار رینگی رونیکس سری کامل",
    category_id: 201,
    brand_id: 3,
    base_price: "1450000",
    original_price: "1700000",
    discount_percent: 14,
    stock_quantity: "20",
    stock_unit: "pack",
    low_stock: false,
    availability: true,
    warranty_text: "ضمانت اصالت کالا",
    weight_grams: "2400",
    is_original: true,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("ring-wrench"),
    images: [{ id: 9, url: IMG("ring-wrench"), is_primary: true }],
    description: "ست آچار رینگی دوسر رونیکس شامل ۸ عدد در سایزهای متداول.",
    specifications: {
      technical_specs: [
        { key: "تعداد", value: "۸ عدد" },
        { key: "جنس", value: "کروم وانادیوم" },
      ],
      dimensions: [{ key: "وزن خالص", value: "۲۴۰۰" }],
      features: { "جعبه نگهدارنده": true },
    },
    created_at: "2026-02-02T09:00:00Z",
    updated_at: "2026-05-22T09:00:00Z",
  },
  {
    id: 7,
    sku: "GRP-MEC-150",
    name: "گیره مکانیک ۱۵۰ میلی‌متر",
    category_id: 210,
    brand_id: null,
    base_price: null,
    original_price: null,
    discount_percent: null,
    stock_quantity: "9",
    stock_unit: "piece",
    low_stock: true,
    availability: true,
    warranty_text: null,
    weight_grams: "5400",
    is_original: false,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("bench-vise"),
    images: [{ id: 10, url: IMG("bench-vise"), is_primary: true }],
    description:
      "گیره مکانیک رومیزی با فک ۱۵۰ میلی‌متری و بدنه چدنی مقاوم، مناسب کارگاه‌های مکانیکی.",
    specifications: {
      technical_specs: [
        { key: "جنس بدنه", value: "چدن" },
        { key: "عرض فک", value: "۱۵۰ میلی‌متر" },
      ],
      dimensions: [
        { key: "بازشو فک", value: "۱۸۰" },
        { key: "وزن خالص", value: "۵۴۰۰" },
      ],
      features: { "قابلیت چرخش": true, "سندان پشتی": true },
    },
    created_at: "2026-03-20T09:00:00Z",
    updated_at: "2026-06-18T09:00:00Z",
  },
  {
    id: 8,
    sku: "MTY-CAL-150D",
    name: "کولیس دیجیتال میتوتویو ۱۵۰ میلی‌متر",
    category_id: 300,
    brand_id: 4,
    base_price: "8900000",
    original_price: null,
    discount_percent: null,
    stock_quantity: "7",
    stock_unit: "piece",
    low_stock: true,
    availability: true,
    warranty_text: "۲۴ ماه گارانتی اصالت",
    weight_grams: "300",
    is_original: true,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("caliper-mitutoyo"),
    images: [
      { id: 11, url: IMG("caliper-mitutoyo"), is_primary: true },
      { id: 12, url: IMG("caliper-mitutoyo-2"), is_primary: false },
    ],
    description:
      "کولیس دیجیتال میتوتویو با دقت ۰.۰۱ میلی‌متر و نمایشگر LCD، مرجع اندازه‌گیری دقیق در صنعت.",
    specifications: {
      technical_specs: [
        { key: "محدوده اندازه‌گیری", value: "۰ تا ۱۵۰ میلی‌متر" },
        { key: "دقت", value: "۰.۰۱ میلی‌متر" },
        { key: "جنس", value: "استیل ضدزنگ" },
      ],
      dimensions: [{ key: "وزن خالص", value: "۳۰۰" }],
      features: { "نمایشگر دیجیتال": true, "خروجی داده": true },
    },
    created_at: "2026-01-05T09:00:00Z",
    updated_at: "2026-06-20T09:00:00Z",
  },
  {
    id: 9,
    sku: "MTY-MIC-25",
    name: "میکرومتر میتوتویو ۲۵-۰ میلی‌متر",
    category_id: 301,
    brand_id: 4,
    base_price: "6200000",
    original_price: "6900000",
    discount_percent: 10,
    stock_quantity: "5",
    stock_unit: "piece",
    low_stock: true,
    availability: true,
    warranty_text: "۲۴ ماه گارانتی اصالت",
    weight_grams: "230",
    is_original: true,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("micrometer"),
    images: [{ id: 13, url: IMG("micrometer"), is_primary: true }],
    description: "میکرومتر خارج‌سنج میتوتویو با دقت بالا برای اندازه‌گیری ظریف.",
    specifications: {
      technical_specs: [
        { key: "محدوده", value: "۰ تا ۲۵ میلی‌متر" },
        { key: "دقت", value: "۰.۰۰۱ میلی‌متر" },
      ],
      dimensions: [{ key: "وزن خالص", value: "۲۳۰" }],
      features: { "قفل اسپیندل": true },
    },
    created_at: "2026-02-18T09:00:00Z",
    updated_at: "2026-06-21T09:00:00Z",
  },
  {
    id: 10,
    sku: "MKT-9555",
    name: "فرز ماکیتا مدل 9555NB",
    category_id: 110,
    brand_id: 2,
    base_price: "3950000",
    original_price: null,
    discount_percent: null,
    stock_quantity: "0",
    stock_unit: "piece",
    low_stock: false,
    availability: false,
    warranty_text: "۱۲ ماه گارانتی",
    weight_grams: "2100",
    is_original: true,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("grinder-makita"),
    images: [{ id: 14, url: IMG("grinder-makita"), is_primary: true }],
    description: "مینی فرز ماکیتا با بدنه باریک و قابلیت کنترل بهتر.",
    specifications: {
      technical_specs: [
        { key: "توان موتور", value: "۷۱۰ وات" },
        { key: "قطر صفحه", value: "۱۱۵ میلی‌متر" },
      ],
      dimensions: [{ key: "وزن خالص", value: "۲۱۰۰" }],
      features: { "دسته باریک": true },
    },
    created_at: "2026-03-25T09:00:00Z",
    updated_at: "2026-06-22T09:00:00Z",
  },
  {
    id: 11,
    sku: "RNX-PLR-180",
    name: "انبردست رونیکس ۱۸۰ میلی‌متر",
    category_id: 211,
    brand_id: 3,
    base_price: "420000",
    original_price: null,
    discount_percent: null,
    stock_quantity: "60",
    stock_unit: "piece",
    low_stock: false,
    availability: true,
    warranty_text: "ضمانت اصالت کالا",
    weight_grams: "320",
    is_original: true,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("pliers"),
    images: [{ id: 15, url: IMG("pliers"), is_primary: true }],
    description: "انبردست رونیکس با دسته عایق و فک سخت‌کاری شده.",
    specifications: {
      technical_specs: [{ key: "جنس", value: "کروم وانادیوم" }],
      dimensions: [{ key: "طول", value: "۱۸۰" }],
      features: { "دسته عایق": true },
    },
    created_at: "2026-04-01T09:00:00Z",
    updated_at: "2026-06-23T09:00:00Z",
  },
  {
    id: 12,
    sku: "TBL-VISE-200",
    name: "گیره رومیزی صنعتی ۲۰۰ میلی‌متر",
    category_id: 400,
    brand_id: null,
    base_price: null,
    original_price: null,
    discount_percent: null,
    stock_quantity: "14",
    stock_unit: "piece",
    low_stock: false,
    availability: true,
    warranty_text: null,
    weight_grams: "9200",
    is_original: false,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: IMG("table-vise"),
    images: [{ id: 16, url: IMG("table-vise"), is_primary: true }],
    description: "گیره رومیزی صنعتی با فک ۲۰۰ میلی‌متری و قابلیت گردش ۳۶۰ درجه.",
    specifications: {
      technical_specs: [
        { key: "عرض فک", value: "۲۰۰ میلی‌متر" },
        { key: "جنس بدنه", value: "چدن" },
      ],
      dimensions: [{ key: "وزن خالص", value: "۹۲۰۰" }],
      features: { "گردش ۳۶۰ درجه": true, "سندان پشتی": true },
    },
    created_at: "2026-04-05T09:00:00Z",
    updated_at: "2026-06-24T09:00:00Z",
  },
];

export const PRODUCTS = expandProducts(BASE_PRODUCTS, CATEGORIES);

/* -------------------------------------------------------------------------- */
/*  Product comments.                                                          */
/* -------------------------------------------------------------------------- */
export const COMMENTS: ProductComment[] = [
  {
    id: 1,
    product_id: 1,
    author_name: "رضا محمدی",
    rating: 5,
    body: "کیفیت ساخت عالی، برای سوراخ‌کاری بتن بی‌نقص کار می‌کنه.",
    created_at: "2026-05-12T10:00:00Z",
    is_verified_buyer: true,
  },
  {
    id: 2,
    product_id: 1,
    author_name: "سعید کریمی",
    rating: 4,
    body: "قدرتش خوبه ولی کاش کیف حملش هم همراهش بود.",
    created_at: "2026-05-20T10:00:00Z",
    is_verified_buyer: true,
  },
  {
    id: 3,
    product_id: 8,
    author_name: "مهندس فلاح",
    rating: 5,
    body: "دقت اندازه‌گیری فوق‌العاده، همون چیزی که از میتوتویو انتظار داری.",
    created_at: "2026-06-01T10:00:00Z",
    is_verified_buyer: true,
  },
];

/* -------------------------------------------------------------------------- */
/*  Articles (related content on PDP / blog teasers).                          */
/* -------------------------------------------------------------------------- */
export const ARTICLES: Article[] = [
  {
    id: 4,
    slug: VERNIER_CALIPER_ARTICLE.slug,
    title: "آموزش خواندن کولیس ورنیه",
    excerpt: VERNIER_CALIPER_ARTICLE.excerpt,
    cover_image: VERNIER_CALIPER_ARTICLE.cover_image,
    published_at: VERNIER_CALIPER_ARTICLE.published_at,
    reading_minutes: VERNIER_CALIPER_ARTICLE.reading_minutes,
  },
  {
    id: 1,
    slug: "how-to-choose-drill",
    title: "راهنمای کامل انتخاب دریل مناسب",
    excerpt: "از دریل چکشی تا شارژی؛ کدام برای کار شما مناسب‌تر است؟",
    cover_image: IMG("article-drill"),
    published_at: "2026-05-01T10:00:00Z",
    reading_minutes: 6,
  },
  {
    id: 2,
    slug: "caliper-accuracy",
    title: "نگهداری و کالیبراسیون کولیس دیجیتال",
    excerpt: "چند نکته کلیدی برای حفظ دقت ابزار اندازه‌گیری شما.",
    cover_image: IMG("article-caliper"),
    published_at: "2026-05-18T10:00:00Z",
    reading_minutes: 4,
  },
  {
    id: 3,
    slug: "workshop-safety",
    title: "اصول ایمنی در کار با ابزار برقی",
    excerpt: "ایمنی را جدی بگیرید؛ راهنمای حرفه‌ای‌ها برای کارگاه.",
    cover_image: IMG("article-safety"),
    published_at: "2026-06-02T10:00:00Z",
    reading_minutes: 8,
  },
];

/* -------------------------------------------------------------------------- */
/*  Blog posts (full content keyed by slug; teasers reuse the Article fields). */
/* -------------------------------------------------------------------------- */
export const BLOG_POSTS: BlogPost[] = [
  {
    id: 4,
    ...VERNIER_CALIPER_ARTICLE,
  },
  {
    id: 1,
    slug: "how-to-choose-drill",
    title: "راهنمای کامل انتخاب دریل مناسب",
    excerpt: "از دریل چکشی تا شارژی؛ کدام برای کار شما مناسب‌تر است؟",
    cover_image: IMG("article-drill"),
    published_at: "2026-05-01T10:00:00Z",
    reading_minutes: 6,
    author: "تیم فنی کارزار",
    tags: ["دریل", "ابزار برقی", "راهنمای خرید"],
    related_product_ids: [1, 2],
    blocks: [
      {
        type: "paragraph",
        text: "انتخاب دریل مناسب یکی از مهم‌ترین تصمیم‌ها برای هر صنعتگر یا علاقه‌مند به کارهای فنی است. در این مقاله انواع دریل و کاربرد هرکدام را بررسی می‌کنیم تا با خیال راحت خرید کنید.",
      },
      { type: "heading", text: "دریل چکشی یا شارژی؟" },
      {
        type: "paragraph",
        text: "دریل چکشی برای سوراخ‌کاری بتن و مصالح سخت بهترین گزینه است، در حالی که دریل شارژی تحرک و راحتی بیشتری برای کارهای سبک و پیچ‌گوشتی فراهم می‌کند.",
      },
      { type: "heading", text: "نکات کلیدی هنگام خرید" },
      {
        type: "list",
        items: [
          "توان موتور را متناسب با نوع کار انتخاب کنید.",
          "وجود قابلیت تنظیم دور برای کنترل بهتر مهم است.",
          "وزن و ارگونومی در کارهای طولانی تأثیر زیادی دارد.",
          "گارانتی و خدمات پس از فروش را بررسی کنید.",
        ],
      },
      {
        type: "paragraph",
        text: "در فروشگاه کارزار می‌توانید از میان معتبرترین برندها انتخاب کنید و در صورت نیاز از مشاوره تخصصی تیم ما بهره‌مند شوید.",
      },
    ],
  },
  {
    id: 2,
    slug: "caliper-accuracy",
    title: "نگهداری و کالیبراسیون کولیس دیجیتال",
    excerpt: "چند نکته کلیدی برای حفظ دقت ابزار اندازه‌گیری شما.",
    cover_image: IMG("article-caliper"),
    published_at: "2026-05-18T10:00:00Z",
    reading_minutes: 4,
    author: "واحد اندازه‌گیری کارزار",
    tags: ["کولیس", "اندازه‌گیری", "کالیبراسیون"],
    related_product_ids: [8, 9],
    blocks: [
      {
        type: "paragraph",
        text: "ابزار اندازه‌گیری دقیق تنها زمانی ارزشمند است که دقت آن حفظ شود. کولیس دیجیتال نیز نیازمند مراقبت و کالیبراسیون دوره‌ای است.",
      },
      { type: "heading", text: "نگهداری صحیح" },
      {
        type: "list",
        items: [
          "پس از هر بار استفاده فک‌ها را تمیز کنید.",
          "از ضربه و افتادن ابزار جلوگیری کنید.",
          "باتری را در صورت عدم استفاده طولانی خارج کنید.",
        ],
      },
      {
        type: "paragraph",
        text: "کالیبراسیون سالانه توسط مراکز معتبر، اطمینان از صحت اندازه‌گیری را تضمین می‌کند.",
      },
    ],
  },
  {
    id: 3,
    slug: "workshop-safety",
    title: "اصول ایمنی در کار با ابزار برقی",
    excerpt: "ایمنی را جدی بگیرید؛ راهنمای حرفه‌ای‌ها برای کارگاه.",
    cover_image: IMG("article-safety"),
    published_at: "2026-06-02T10:00:00Z",
    reading_minutes: 8,
    author: "تیم ایمنی کارزار",
    tags: ["ایمنی", "کارگاه", "ابزار برقی"],
    related_product_ids: [3, 4, 10],
    blocks: [
      {
        type: "paragraph",
        text: "کار با ابزار برقی بدون رعایت اصول ایمنی می‌تواند خطرناک باشد. رعایت چند نکته ساده از بروز حوادث جلوگیری می‌کند.",
      },
      { type: "heading", text: "تجهیزات حفاظت فردی" },
      {
        type: "list",
        items: [
          "همیشه از عینک ایمنی استفاده کنید.",
          "گوشی محافظ در برابر صدای زیاد ضروری است.",
          "دستکش مناسب و لباس کار بپوشید.",
        ],
      },
      {
        type: "paragraph",
        text: "پیش از روشن کردن دستگاه، از سالم بودن کابل و اتصالات مطمئن شوید و محیط کار را مرتب نگه دارید.",
      },
    ],
  },
];

/* -------------------------------------------------------------------------- */
/*  Hero slides.                                                               */
/* -------------------------------------------------------------------------- */
export const HERO_SLIDES: HeroSlide[] = [
  {
    id: 1,
    title: "ابزار اندازه‌گیری دقیق",
    subtitle:
      "کولیس، میکرومتر و گیج‌های صنعتی از برندهای معتبر — موجودی و استعلام برای خط تولید شما",
    cta_label: "مشاهده محصولات",
    cta_href: "/catalog",
    image: "/images/hero/hero-micrometer-rtl.png",
    accent: "#C22026",
  },
];
