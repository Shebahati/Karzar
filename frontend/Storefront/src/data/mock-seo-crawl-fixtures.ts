/**
 * Deterministic mock catalog rows for SEO Wave 1B HTTP crawl contracts.
 * Uses a non-placeholder public image (not under /images/placeholders/).
 */

import type { ProductDetail } from "@/types/product";

/** Repo public asset — passes `isPlaceholderImageUrl` / `hasPublicProductImage`. */
export const SEO_CRAWL_PRODUCT_IMAGE = "/images/brands/mitutoyo.svg";

export const SEO_CRAWL_CATEGORY_SLUG = "kolis-mikrometr";
export const SEO_CRAWL_CATEGORY_HUB_ID = 101;
export const SEO_CRAWL_LEAF_CATEGORY_ID = 1001;
export const SEO_CRAWL_BRAND_ID = 1;
export const SEO_CRAWL_BRAND_SLUG = "bosch";

/** Public but unavailable — PDP OutOfStock + PLP discovery regression. */
export const SEO_CRAWL_OOS_PRODUCT_SLUG = "seo-crawl-oos";

/** Minimum crawlable PLP rows (2+ pages at CATALOG_PAGE_SIZE=20). */
export const SEO_CRAWL_PRODUCT_TARGET = 45;

type RawProduct = Omit<ProductDetail, "category" | "brand" | "stock_status"> & {
  category_id: number;
  brand_id: number | null;
};

const TEMPLATE: Omit<RawProduct, "id" | "sku" | "name" | "category_id" | "brand_id"> = {
  base_price: "1250000",
  original_price: null,
  discount_percent: null,
  stock_quantity: "12",
  stock_unit: "piece",
  low_stock: false,
  availability: true,
  warranty_text: "ضمانت اصالت",
  weight_grams: "500",
  is_original: true,
  tax_percent: "9",
  is_active: true,
  pdf_catalog_url: null,
  thumbnail: SEO_CRAWL_PRODUCT_IMAGE,
  images: [{ id: 1, url: SEO_CRAWL_PRODUCT_IMAGE, is_primary: true }],
  description: "محصول آزمایشی crawl برای قرارداد SEO Wave 1B.",
  specifications: {
    technical_specs: [{ key: "fixture", value: "seo-wave1b" }],
    dimensions: [{ key: "وزن خالص", value: "۵۰۰" }],
    features: { "crawl-fixture": true },
  },
  created_at: "2026-06-01T09:00:00Z",
  updated_at: "2026-06-01T09:00:00Z",
};

export function buildSeoCrawlOosProduct(): RawProduct {
  return {
    ...TEMPLATE,
    id: 880_050,
    sku: "SEO-CRAWL-OOS",
    name: "محصول crawl ناموجود آزمایشی",
    category_id: SEO_CRAWL_LEAF_CATEGORY_ID,
    brand_id: SEO_CRAWL_BRAND_ID,
    availability: false,
    stock_quantity: "0",
  };
}

export function buildSeoCrawlFixtureProducts(): RawProduct[] {
  const startId = 880_001;
  const rows = Array.from({ length: SEO_CRAWL_PRODUCT_TARGET }, (_, i) => {
    const n = i + 1;
    const id = startId + i;
    return {
      ...TEMPLATE,
      id,
      sku: `SEO-CRAWL-${String(n).padStart(3, "0")}`,
      name: `محصول crawl آزمایشی ${n}`,
      category_id: SEO_CRAWL_LEAF_CATEGORY_ID,
      brand_id: SEO_CRAWL_BRAND_ID,
    };
  });
  return [...rows, buildSeoCrawlOosProduct()];
}

export function buildSeoCrawlBlogTeasers(): Array<{
  id: number;
  slug: string;
  title: string;
  excerpt: string;
  cover_image: string;
  published_at: string;
  reading_minutes: number;
}> {
  const base = "2026-06-15T10:00:00Z";
  return Array.from({ length: 25 }, (_, i) => {
    const n = i + 1;
    return {
      id: 90_000 + n,
      slug: `seo-wave1b-blog-${n}`,
      title: `مقاله crawl آزمایشی ${n}`,
      excerpt: "قرارداد صفحه‌بندی مجله در Wave 1B.",
      cover_image: SEO_CRAWL_PRODUCT_IMAGE,
      published_at: new Date(Date.parse(base) + n * 3600_000).toISOString(),
      reading_minutes: 3,
    };
  });
}
