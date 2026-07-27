import type { MetadataRoute } from "next";
import { capSitemapEntries } from "@/lib/crawl-hygiene";
import { getSiteUrl } from "@/lib/site-url";
import { catalogService } from "@/services/catalog";

const PRODUCT_PAGE_SIZE = 1000;
/** Hard cap so a runaway API cannot blow sitemap generation. */
const MAX_PRODUCT_PAGES = 20;

async function collectProductEntries(
  site: string,
  now: Date,
): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];
  let skip = 0;

  for (let page = 0; page < MAX_PRODUCT_PAGES; page += 1) {
    const result = await catalogService.listProducts({
      skip,
      limit: PRODUCT_PAGE_SIZE,
      sort: "newest",
    });

    for (const product of result.data) {
      const lastModified = product.updated_at
        ? new Date(product.updated_at)
        : now;
      entries.push({
        url: `${site}/product/${product.id}`,
        lastModified,
        changeFrequency: "weekly",
        priority: 0.8,
      });
    }

    if (!result.meta.has_next || result.data.length === 0) break;
    skip += PRODUCT_PAGE_SIZE;
  }

  return entries;
}

async function collectCategoryEntries(
  site: string,
  now: Date,
): Promise<MetadataRoute.Sitemap> {
  try {
    const categories = await catalogService.listCategoriesFlat();
    // Skip empty hubs (soft-404) — only index categories with products.
    return categories
      .filter((c) => (c.product_count ?? 0) > 0 && c.slug)
      .map((c) => ({
        url: `${site}/categories/${c.slug}`,
        lastModified: now,
        changeFrequency: "weekly" as const,
        priority: c.depth === 1 ? 0.85 : 0.7,
      }));
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const site = getSiteUrl();
  const now = new Date();
  const staticPaths = ["", "/catalog", "/blog", "/about", "/contact", "/terms", "/privacy"];

  const staticEntries: MetadataRoute.Sitemap = staticPaths.map((path) => ({
    url: `${site}${path || "/"}`,
    lastModified: now,
    changeFrequency: path === "" || path === "/catalog" ? "daily" : "weekly",
    priority: path === "" ? 1 : path === "/blog" ? 0.8 : 0.7,
  }));

  let blogEntries: MetadataRoute.Sitemap = [];
  try {
    const articles = await catalogService.listArticles();
    blogEntries = articles.map((a) => ({
      url: `${site}/blog/${a.slug}`,
      lastModified: a.published_at ? new Date(a.published_at) : now,
      changeFrequency: "monthly" as const,
      priority: 0.75,
    }));
  } catch {
    blogEntries = [];
  }

  let productEntries: MetadataRoute.Sitemap = [];
  try {
    productEntries = await collectProductEntries(site, now);
  } catch {
    productEntries = [];
  }

  const categoryEntries = await collectCategoryEntries(site, now);

  return capSitemapEntries([
    ...staticEntries,
    ...categoryEntries,
    ...blogEntries,
    ...productEntries,
  ]);
}
