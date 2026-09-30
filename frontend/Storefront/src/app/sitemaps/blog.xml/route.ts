import { collectBlogEntries } from "@/lib/sitemap/collect";
import { handleSitemapRoute } from "@/lib/sitemap/http";
import { buildUrlsetXml } from "@/lib/sitemap/xml";

export async function GET(): Promise<Response> {
  return handleSitemapRoute("blog", async () => {
    const { entries, entryCount } = await collectBlogEntries();
    console.info(`[sitemap] blog entries=${entryCount}`);
    return buildUrlsetXml(entries);
  });
}
