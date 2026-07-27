/**
 * Single origin for canonicals, sitemap, robots, and JSON-LD (SEO-004).
 *
 * Override with NEXT_PUBLIC_SITE_URL (absolute origin). Defaults to production www.
 * Live deploy topology currently serves karzartools.com from the "staging" VPS —
 * leave indexable unless NEXT_PUBLIC_SEO_INDEXABLE=false (preview/non-public hosts).
 */

export const DEFAULT_SITE_URL = "https://www.karzartools.com";

export function getSiteUrl(): string {
  const raw = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  if (raw) {
    try {
      const withProtocol = raw.includes("://") ? raw : `https://${raw}`;
      return new URL(withProtocol).origin;
    } catch {
      /* fall through to default */
    }
  }
  return DEFAULT_SITE_URL;
}

/** Whether this build should allow indexing (robots allow + meta index). */
export function isSeoIndexable(): boolean {
  const flag = process.env.NEXT_PUBLIC_SEO_INDEXABLE?.trim().toLowerCase();
  if (flag === "false" || flag === "0" || flag === "no") return false;
  if (flag === "true" || flag === "1" || flag === "yes") return true;
  return true;
}
