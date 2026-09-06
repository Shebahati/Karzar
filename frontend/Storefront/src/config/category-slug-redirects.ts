/**
 * Permanent 301 redirects for renamed category slugs (taxonomy migration).
 * Keys and values are URL path segments (decoded slug), not full paths.
 */
export const CATEGORY_SLUG_REDIRECTS: Readonly<Record<string, string>> = {
  // Populated by scripts/catalog_taxonomy_migrate.py --apply when slugs change.
};

export function resolveCategorySlugRedirect(slug: string): string | null {
  const trimmed = slug.trim();
  if (!trimmed) return null;
  return CATEGORY_SLUG_REDIRECTS[trimmed] ?? null;
}
