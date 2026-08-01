/**
 * Local brand logo paths under Storefront `public/images/brands/`.
 * Used when API `logo_url` is null (Brand ORM in Karzar-main has no logo column yet).
 * Keys are the English name before `|` in seed names, lowercased.
 */
const BRAND_LOGOS: Record<string, string> = {
  mitutoyo: "/images/brands/mitutoyo.svg",
  insize: "/images/brands/insize.png",
  "mighty seven": "/images/brands/mighty-seven.png",
};

/** English key from `"Mitutoyo | میتوتویو"` → `"mitutoyo"`. */
export function brandEnglishKey(name: string): string {
  return (name.split("|")[0] ?? name).trim().toLowerCase();
}

/**
 * Prefer API `logo_url`; otherwise map by English brand name to a local asset.
 */
export function resolveBrandLogoUrl(
  name: string,
  logoUrl?: string | null,
): string | null {
  const fromApi = logoUrl?.trim();
  if (fromApi) return fromApi;
  return BRAND_LOGOS[brandEnglishKey(name)] ?? null;
}
