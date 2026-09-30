import { collectCategoryEntries } from "@/lib/sitemap/collect";
import { handleSitemapRoute } from "@/lib/sitemap/http";
import { buildUrlsetXml } from "@/lib/sitemap/xml";

export async function GET(): Promise<Response> {
  return handleSitemapRoute("categories", async () => {
    const { entries, entryCount } = await collectCategoryEntries();
    console.info(`[sitemap] categories entries=${entryCount}`);
    return buildUrlsetXml(entries);
  });
}
