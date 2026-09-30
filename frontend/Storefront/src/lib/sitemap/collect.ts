import { SITEMAP_STATIC_PATHS } from "@/lib/crawl-hygiene";
import { productPath } from "@/lib/product-url";
import { getSiteUrl } from "@/lib/site-url";
import { catalogService } from "@/services/catalog";
import {
  PRODUCT_SITEMAP_SHARD_SIZE,
  SITEMAP_PRODUCT_SORT,
} from "./constants";
import { SitemapGenerationError, SitemapNotFoundError } from "./errors";
import { articleLastmod, productLastmod } from "./lastmod";
import {
  assertShardUrlCountWithinProtocolLimit,
  isValidProductShardIndex,
  productShardCount,
  productShardSkip,
} from "./shard";
import type { SitemapUrlEntry } from "./xml";
import { validateUrlEntries } from "./validate";

export type SitemapCollectResult = {
  entries: SitemapUrlEntry[];
  entryCount: number;
};

function siteBase(): string {
  return getSiteUrl();
}

export function collectStaticEntries(): SitemapCollectResult {
  const site = siteBase();
  const entries: SitemapUrlEntry[] = SITEMAP_STATIC_PATHS.map((path) => ({
    loc: `${site}${path}`,
  }));
  validateUrlEntries(entries, site);
  return { entries, entryCount: entries.length };
}

export async function collectCategoryEntries(): Promise<SitemapCollectResult> {
  const site = siteBase();
  try {
    const categories = await catalogService.listCategoriesFlat();
    const entries: SitemapUrlEntry[] = categories
      .filter((c) => (c.product_count ?? 0) > 0 && c.slug)
      .map((c) => ({
        loc: `${site}/categories/${c.slug}`,
      }));
    validateUrlEntries(entries, site);
    return { entries, entryCount: entries.length };
  } catch (error) {
    throw new SitemapGenerationError("categories", undefined, { cause: error });
  }
}

export async function collectBrandEntries(): Promise<SitemapCollectResult> {
  const site = siteBase();
  try {
    const brands = await catalogService.listBrands();
    const entries: SitemapUrlEntry[] = brands
      .filter((b) => (b.product_count ?? 0) >= 1 && Boolean(b.slug?.trim()))
      .map((b) => ({
        loc: `${site}/brands/${b.slug!.trim()}`,
      }));
    validateUrlEntries(entries, site);
    return { entries, entryCount: entries.length };
  } catch (error) {
    throw new SitemapGenerationError("brands", undefined, { cause: error });
  }
}

export async function collectBlogEntries(): Promise<SitemapCollectResult> {
  const site = siteBase();
  try {
    const articles = await catalogService.listArticles();
    const entries: SitemapUrlEntry[] = articles.map((a) => ({
      loc: `${site}/blog/${a.slug}`,
      lastmod: articleLastmod(a.published_at),
    }));
    validateUrlEntries(entries, site);
    return { entries, entryCount: entries.length };
  } catch (error) {
    throw new SitemapGenerationError("blog", undefined, { cause: error });
  }
}

export async function fetchPublicProductTotalCount(): Promise<number> {
  try {
    const result = await catalogService.listProducts({
      skip: 0,
      limit: 1,
      sort: SITEMAP_PRODUCT_SORT,
    });
    return result.meta.total_count ?? 0;
  } catch (error) {
    throw new SitemapGenerationError("product_count", undefined, { cause: error });
  }
}

export async function collectProductShardEntries(
  shardIndex: number,
): Promise<SitemapCollectResult> {
  const site = siteBase();
  const total = await fetchPublicProductTotalCount();
  if (!isValidProductShardIndex(shardIndex, total)) {
    throw new SitemapNotFoundError(`Invalid product sitemap shard index: ${shardIndex}`);
  }

  const shardCount = productShardCount(total);
  const isFinalShard = shardIndex === shardCount - 1 || total === 0;

  try {
    const result = await catalogService.listProducts({
      skip: productShardSkip(shardIndex),
      limit: PRODUCT_SITEMAP_SHARD_SIZE,
      sort: SITEMAP_PRODUCT_SORT,
    });

    const rows = result.data;
    if (!isFinalShard && rows.length < PRODUCT_SITEMAP_SHARD_SIZE) {
      throw new SitemapGenerationError(
        "product_shard",
        `Shard ${shardIndex} truncated: expected ${PRODUCT_SITEMAP_SHARD_SIZE} rows, got ${rows.length} (total_count=${total})`,
      );
    }

    const entries: SitemapUrlEntry[] = rows.map((product) => ({
      loc: `${site}${productPath(product)}`,
      lastmod: productLastmod(product.updated_at),
    }));

    assertShardUrlCountWithinProtocolLimit(entries.length);
    validateUrlEntries(entries, site);

    for (const product of rows) {
      const path = productPath(product);
      if (/^\/product\/\d+$/.test(path)) {
        throw new SitemapGenerationError(
          "product_shard",
          `Numeric product URL in sitemap: ${path}`,
        );
      }
    }

    return { entries, entryCount: entries.length };
  } catch (error) {
    if (error instanceof SitemapGenerationError) throw error;
    throw new SitemapGenerationError("product_shard", undefined, { cause: error });
  }
}
