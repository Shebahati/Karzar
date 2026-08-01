/**
 * Product public URL helpers (EPIC 1 / ADR-010 / RFC-004).
 * Prefer slug; fall back to numeric id only when slug is missing.
 */

export function isNumericProductParam(param: string): boolean {
  return /^\d+$/.test(param.trim());
}

/**
 * Decode a route/API slug segment once. Already-decoded Unicode and
 * malformed percent-sequences are returned unchanged (never throws).
 */
export function safeDecodeURIComponent(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

/**
 * Encode a product slug for an API path segment: decode-once then encode-once
 * so a pre-encoded Next.js param is never percent-encoded again.
 */
export function encodeSlugPathSegment(slug: string): string {
  return encodeURIComponent(safeDecodeURIComponent(slug.trim()));
}

export function productPath(product: {
  id: number;
  slug?: string | null;
}): string {
  const slug = product.slug?.trim();
  if (slug) return `/product/${slug}`;
  return `/product/${product.id}`;
}
