import { buildSitemapIndexXmlDocument } from "@/lib/sitemap/index-document";
import {
  handleSitemapRoute,
  sitemapXmlServiceUnavailable,
} from "@/lib/sitemap/http";
import { SitemapGenerationError } from "@/lib/sitemap/errors";

export async function GET(): Promise<Response> {
  try {
    const { xml, productShards, publicProductCount } =
      await buildSitemapIndexXmlDocument();
    return handleSitemapRoute("index", () => xml, {
      "X-Karzar-Sitemap-Shards": String(productShards),
      "X-Karzar-Sitemap-Public-Products": String(publicProductCount),
    });
  } catch (error) {
    if (error instanceof SitemapGenerationError) {
      return sitemapXmlServiceUnavailable(error.cohort, error.cause ?? error);
    }
    return sitemapXmlServiceUnavailable("index", error);
  }
}
