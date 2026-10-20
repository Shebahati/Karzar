/**
 * Optimized delivery for curated `/category-icons/*.png` assets.
 *
 * `NEXT_PUBLIC_CATEGORY_ICON_WEBP` is read at **build time** only (inlined into the bundle).
 * Default is OFF — do not set in production build env until Owner explicitly authorizes.
 * Enabling or disabling requires a new build; runtime env changes do not toggle delivery.
 */

import { isCuratedCategoryIconPngUrl } from "@/config/category-icon-allowlist";
import { CATEGORY_ICON_DIR } from "@/config/category-icons";

const WEBP_DIR = `${CATEGORY_ICON_DIR}/webp`;

export function categoryIconWebpExperimentEnabled(): boolean {
  const flag = process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP?.trim().toLowerCase();
  return flag === "1" || flag === "true" || flag === "yes";
}

/**
 * Allowlisted curated PNG only → paired WebP when experiment flag is on at build time.
 * Unknown `/category-icons/foo.png`, external URLs, or flag off → null (use original src only).
 */
export function resolveCategoryIconSources(
  iconUrl: string,
): { png: string; webp: string } | null {
  const trimmed = iconUrl.trim();
  if (!categoryIconWebpExperimentEnabled()) {
    return null;
  }
  if (!isCuratedCategoryIconPngUrl(trimmed)) {
    return null;
  }
  const base = trimmed.slice(CATEGORY_ICON_DIR.length + 1, -4);
  return {
    png: trimmed,
    webp: `${WEBP_DIR}/${base}.webp`,
  };
}
