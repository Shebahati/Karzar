/**
 * Technical SEO crawl hygiene helpers (SEO-004).
 *
 * - Faceted/filter query params are crawl traps → noindex,follow + clean canonical.
 * - Empty category hubs are soft-404s → hard 404 (notFound).
 * - Sitemap must stay under Google's 50k URL / file limit.
 */

import type { Metadata } from "next";

/** Google soft limit; keep headroom under 50_000. */
export const MAX_SITEMAP_URLS = 49_000;

export const NOINDEX_NOFOLLOW: Metadata["robots"] = {
  index: false,
  follow: false,
};

export const NOINDEX_FOLLOW: Metadata["robots"] = {
  index: false,
  follow: true,
};

/** Paths disallowed in robots.txt (private / transactional). */
export const ROBOTS_DISALLOW = [
  "/account/",
  "/checkout/",
  "/cart",
  "/login",
  "/quote",
] as const;

/**
 * Self-canonical paths for indexable static routes (resolved via metadataBase).
 * Root layout must NOT set a sitewide canonical — descendants inherit it.
 */
export const INDEXABLE_STATIC_CANONICALS = {
  home: "/",
  about: "/about",
  contact: "/contact",
  terms: "/terms",
  faq: "/faq",
  blog: "/blog",
  catalog: "/catalog",
  categories: "/categories",
} as const;

/** Static sitemap entries: public canonical URLs only (no private/facet/legacy). */
export const SITEMAP_STATIC_PATHS = [
  "/",
  "/catalog",
  "/blog",
  "/about",
  "/contact",
  "/terms",
  "/faq",
] as const;

/** Next.js Metadata.alternates for a self-canonical path (via metadataBase). */
export function selfCanonicalAlternates(
  pathname: string,
): NonNullable<Metadata["alternates"]> {
  return { canonical: pathname };
}

/**
 * Query keys that create near-duplicate PLP/hub URLs.
 * Pagination is client-state only (not in the URL) — not listed here.
 */
const FACET_KEYS = new Set([
  "brand",
  "brand_id",
  "brand_slug",
  "country",
  "min_price",
  "max_price",
  "in_stock",
  "on_sale",
  "search",
  "sort",
  "roots",
  "category",
  "category_id",
  "category_slug",
]);

/** On `/categories/{slug}` hubs, CatalogView may mirror the locked id as ?category= — not a trap. */
const HUB_IGNORED_FACET_KEYS = new Set([
  "category",
  "category_id",
  "category_slug",
]);

type SearchParamValue = string | string[] | undefined;

export type FacetedSearchOptions = {
  /** Ignore redundant category_* keys (category hub path is already the indexable URL). */
  ignoreCategoryKeys?: boolean;
};

function hasNonEmptyParam(value: SearchParamValue): boolean {
  if (value == null) return false;
  if (Array.isArray(value)) return value.some((v) => v != null && String(v).trim() !== "");
  return String(value).trim() !== "";
}

/** True when URL search params would create a filter/facet crawl trap. */
export function isFacetedSearchParams(
  searchParams: Record<string, SearchParamValue>,
  options: FacetedSearchOptions = {},
): boolean {
  for (const [key, value] of Object.entries(searchParams)) {
    if (!hasNonEmptyParam(value)) continue;
    if (options.ignoreCategoryKeys && HUB_IGNORED_FACET_KEYS.has(key)) continue;
    if (key.startsWith("spec_")) return true;
    if (FACET_KEYS.has(key)) return true;
  }
  return false;
}

/** Empty hubs with a known zero product_count must not return 200 soft-404. */
export function isEmptyCategoryHub(productCount: number | null | undefined): boolean {
  return typeof productCount === "number" && productCount <= 0;
}

/** Cap sitemap entries under the 50k limit (static + dynamic combined). */
export function capSitemapEntries<T>(entries: T[], max = MAX_SITEMAP_URLS): T[] {
  if (entries.length <= max) return entries;
  return entries.slice(0, max);
}
