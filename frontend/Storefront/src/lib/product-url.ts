/** Canonical storefront product detail URL (slug preferred, numeric id fallback). */
export function productHref(product: { id: number; slug?: string | null }): string {
  return `/product/${product.slug || product.id}`;
}
