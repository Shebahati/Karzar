import { collectProductShardEntries } from "@/lib/sitemap/collect";
import { SitemapNotFoundError } from "@/lib/sitemap/errors";
import {
  handleSitemapRoute,
  sitemapXmlNotFound,
  sitemapXmlServiceUnavailable,
} from "@/lib/sitemap/http";
import { parseProductShardParam } from "@/lib/sitemap/parse-shard";
import { buildUrlsetXml } from "@/lib/sitemap/xml";
import { SitemapGenerationError } from "@/lib/sitemap/errors";

type Props = { params: Promise<{ shard: string }> };

export async function GET(_request: Request, { params }: Props): Promise<Response> {
  const { shard: rawShard } = await params;
  const shardIndex = parseProductShardParam(rawShard);
  if (shardIndex == null) {
    return sitemapXmlNotFound();
  }

  try {
    const { entries, entryCount } = await collectProductShardEntries(shardIndex);
    console.info(`[sitemap] product_shard=${shardIndex} entries=${entryCount}`);
    return handleSitemapRoute(
      "product_shard",
      () => buildUrlsetXml(entries),
      {
        "X-Karzar-Sitemap-Entries": String(entryCount),
        "X-Karzar-Sitemap-Shard": String(shardIndex),
      },
    );
  } catch (error) {
    if (error instanceof SitemapNotFoundError) {
      return sitemapXmlNotFound();
    }
    if (error instanceof SitemapGenerationError) {
      return sitemapXmlServiceUnavailable(error.cohort, error.cause ?? error);
    }
    return sitemapXmlServiceUnavailable("product_shard", error);
  }
}
