import { toSafeNextImageSrc } from "@/lib/image-remote-patterns";
import type { ProductImage, ProductSummary } from "@/types/product";

const PLACEHOLDER_PATTERNS = [
  /placeholder/i,
  /woocommerce-placeholder/i,
  /no[-_]?image/i,
  /default[-_]?(image|product)/i,
  /karzar-editorial\.svg/i,
  /\/images\/placeholders\//i,
] as const;

/** True when the URL is null/empty or a known generic placeholder asset. */
export function isPlaceholderImageUrl(url: string | null | undefined): boolean {
  if (!url || !String(url).trim()) return true;
  const normalized = String(url).trim();
  return PLACEHOLDER_PATTERNS.some((pattern) => pattern.test(normalized));
}

/** Ordered unique image URLs safe for next/image (thumbnail first, then gallery). */
export function resolveProductCardImages(product: ProductSummary): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  const push = (url: string | null | undefined) => {
    if (isPlaceholderImageUrl(url)) return;
    const safe = toSafeNextImageSrc(url);
    if (!safe || seen.has(safe)) return;
    seen.add(safe);
    out.push(safe);
  };

  push(product.thumbnail);

  if (product.images?.length) {
    const sorted = [...product.images].sort(
      (a: ProductImage, b: ProductImage) =>
        Number(b.is_primary) - Number(a.is_primary) || a.id - b.id,
    );
    for (const img of sorted) push(img.url);
  }

  return out;
}

/** Storefront lists should not render products without a real displayable image. */
export function hasPublicProductImage(product: ProductSummary): boolean {
  return resolveProductCardImages(product).length > 0;
}
