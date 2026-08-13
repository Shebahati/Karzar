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

/**
 * RFC-004 / ADR-010: `/product/{numeric-id}` permanently redirects to the
 * slug URL when a distinct slug exists. Returns null when the request is
 * already the canonical path (slug route, or id with no slug).
 */
export function numericProductRedirectPath(
  param: string,
  product: { id: number; slug?: string | null },
): string | null {
  const key = param.trim();
  if (!isNumericProductParam(key)) return null;
  const slug = product.slug?.trim();
  if (!slug || slug === key) return null;
  return productPath(product);
}
