/**
 * Safe sitemap lastmod values — never synthesize request-time dates.
 */

/** W3C / Google sitemap lastmod (date or date-time). */
export function formatSitemapLastmod(date: Date): string {
  return date.toISOString();
}

export function parseSitemapLastmod(value: unknown): string | undefined {
  if (value == null) return undefined;
  if (value instanceof Date) {
    if (Number.isNaN(value.getTime())) return undefined;
    return formatSitemapLastmod(value);
  }
  const raw = String(value).trim();
  if (!raw) return undefined;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return undefined;
  return formatSitemapLastmod(parsed);
}

export function productLastmod(updatedAt?: string | null): string | undefined {
  return parseSitemapLastmod(updatedAt);
}

export function articleLastmod(publishedAt?: string | null): string | undefined {
  return parseSitemapLastmod(publishedAt);
}
