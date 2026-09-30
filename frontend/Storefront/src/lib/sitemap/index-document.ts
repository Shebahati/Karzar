import { getSiteUrl } from "@/lib/site-url";
import { SITEMAP_CHILD_PATHS } from "./constants";
import { SitemapGenerationError } from "./errors";
import { fetchPublicProductTotalCount } from "./collect";
import { productShardCount } from "./shard";
import { buildSitemapIndexXml } from "./xml";

export async function buildSitemapIndexXmlDocument(): Promise<{
  xml: string;
  productShards: number;
  publicProductCount: number;
}> {
  const site = getSiteUrl();
  let publicProductCount: number;
  try {
    publicProductCount = await fetchPublicProductTotalCount();
  } catch (error) {
    throw error instanceof SitemapGenerationError
      ? error
      : new SitemapGenerationError("index", undefined, { cause: error });
  }

  const productShards = productShardCount(publicProductCount);
  const childLocs = [
    `${site}${SITEMAP_CHILD_PATHS.static}`,
    `${site}${SITEMAP_CHILD_PATHS.categories}`,
    `${site}${SITEMAP_CHILD_PATHS.brands}`,
    `${site}${SITEMAP_CHILD_PATHS.blog}`,
    ...Array.from({ length: productShards }, (_, i) =>
      `${site}${SITEMAP_CHILD_PATHS.productShard(i)}`,
    ),
  ];

  const xml = buildSitemapIndexXml(childLocs.map((loc) => ({ loc })));
  console.info(
    `[sitemap] index public_products=${publicProductCount} product_shards=${productShards}`,
  );
  return { xml, productShards, publicProductCount };
}
