import { collectBrandEntries } from "@/lib/sitemap/collect";
import { handleSitemapRoute } from "@/lib/sitemap/http";
import { buildUrlsetXml } from "@/lib/sitemap/xml";

export async function GET(): Promise<Response> {
  return handleSitemapRoute("brands", async () => {
    const { entries, entryCount } = await collectBrandEntries();
    console.info(`[sitemap] brands entries=${entryCount}`);
    return buildUrlsetXml(entries);
  });
}
