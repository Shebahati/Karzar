export type SitemapUrlEntry = {
  loc: string;
  lastmod?: string;
};

export function escapeXmlText(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export function buildUrlsetXml(entries: SitemapUrlEntry[]): string {
  const body = entries
    .map((entry) => {
      const lastmod = entry.lastmod
        ? `\n    <lastmod>${escapeXmlText(entry.lastmod)}</lastmod>`
        : "";
      return `  <url>\n    <loc>${escapeXmlText(entry.loc)}</loc>${lastmod}\n  </url>`;
    })
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
}

export function buildSitemapIndexXml(
  sitemapLocs: { loc: string; lastmod?: string }[],
): string {
  const body = sitemapLocs
    .map((entry) => {
      const lastmod = entry.lastmod
        ? `\n    <lastmod>${escapeXmlText(entry.lastmod)}</lastmod>`
        : "";
      return `  <sitemap>\n    <loc>${escapeXmlText(entry.loc)}</loc>${lastmod}\n  </sitemap>`;
    })
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</sitemapindex>\n`;
}
