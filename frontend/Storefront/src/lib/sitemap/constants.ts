/**
 * SEO Wave 1C — sitemap sharding and caching contract.
 *
 * CACHE MODE: CDN/browser caching via `Cache-Control` on sitemap Route Handler responses.
 * REVALIDATION: SITEMAP_REVALIDATE_SECONDS (s-maxage on responses).
 * FAILURE: upstream errors → HTTP 503 (no empty urlset masquerading as success).
 * STALE: Next may serve last successful ISR payload until revalidation; failed regen does not swap in incomplete XML.
 */

/** Public products per product-sitemap shard (well below Google's 50k/file limit). */
export const PRODUCT_SITEMAP_SHARD_SIZE = 1000;

/** Google protocol maximum URLs per sitemap file (guard only — we shard far below this). */
export const SITEMAP_PROTOCOL_MAX_URLS_PER_FILE = 50_000;

/** Revalidate sitemap route handlers on this interval (seconds). */
export const SITEMAP_REVALIDATE_SECONDS = 300;

/**
 * SITEMAP PRODUCT ORDER (authoritative listing contract):
 * - sort key: `id_asc`
 * - PRIMARY: product id ascending
 * - TIE BREAKER: n/a (unique id)
 * - MUTABILITY RISK: new public products increase shard count; ids are stable (no reorder on update).
 */
export const SITEMAP_PRODUCT_SORT = "id_asc" as const;

export const SITEMAP_CHILD_PATHS = {
  static: "/sitemaps/static.xml",
  categories: "/sitemaps/categories.xml",
  brands: "/sitemaps/brands.xml",
  blog: "/sitemaps/blog.xml",
  productShard: (shard: number) => `/sitemaps/products/${shard}.xml`,
} as const;
