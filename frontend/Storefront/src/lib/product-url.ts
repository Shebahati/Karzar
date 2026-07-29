/**
 * Product public URL helpers (EPIC 1 / ADR-010 / RFC-004).
 * Prefer slug; fall back to numeric id only when slug is missing.
 */

export function isNumericProductParam(param: string): boolean {
  return /^\d+$/.test(param.trim());
}

export function productPath(product: {
  id: number;
  slug?: string | null;
}): string {
  const slug = product.slug?.trim();
  if (slug) return `/product/${slug}`;
  return `/product/${product.id}`;
}
