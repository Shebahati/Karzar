/**
 * Curated L1 category icons with generated WebP variants under `/category-icons/webp/`.
 * Must stay in sync with `scripts/generate-category-icon-variants.mjs` output (13 PNGs).
 */
import { CATEGORY_ICON_DIR } from "@/config/category-icons";

/** Basenames (no path) of PNGs that have a verified WebP sibling. */
export const CURATED_CATEGORY_ICON_WEBP_BASENAMES = [
  "abzar-gir",
  "abzar-gireshi",
  "abzar-inserti",
  "abzar-kargahi",
  "andaze-giri",
  "dastgah-sanati",
  "farz-angoshti",
  "ghalaviz",
  "heli-coil",
  "insert",
  "mete",
  "roghan-ravankar",
  "takhfif",
] as const;

export type CuratedCategoryIconBasename = (typeof CURATED_CATEGORY_ICON_WEBP_BASENAMES)[number];

const BASENAME_SET = new Set<string>(CURATED_CATEGORY_ICON_WEBP_BASENAMES);

export function isCuratedCategoryIconPngUrl(iconUrl: string): boolean {
  const trimmed = iconUrl.trim();
  if (!trimmed.startsWith(`${CATEGORY_ICON_DIR}/`) || !trimmed.endsWith(".png")) {
    return false;
  }
  const base = trimmed.slice(CATEGORY_ICON_DIR.length + 1, -4);
  return BASENAME_SET.has(base);
}

export function curatedCategoryIconWebpUrl(basename: CuratedCategoryIconBasename): string {
  return `${CATEGORY_ICON_DIR}/webp/${basename}.webp`;
}
