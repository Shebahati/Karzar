import { SITEMAP_STATIC_PATHS } from "@/lib/crawl-hygiene";
import { collectStaticEntries } from "@/lib/sitemap/collect";
import { handleSitemapRoute } from "@/lib/sitemap/http";
import { buildUrlsetXml } from "@/lib/sitemap/xml";

export async function GET(): Promise<Response> {
  return handleSitemapRoute("static", () => {
    const { entries, entryCount } = collectStaticEntries();
    console.info(`[sitemap] static entries=${entryCount}`);
    return buildUrlsetXml(entries);
  }, { "X-Karzar-Sitemap-Entries": String(SITEMAP_STATIC_PATHS.length) });
}
