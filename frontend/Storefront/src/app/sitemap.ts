import type { MetadataRoute } from "next";
import { catalogService } from "@/services/catalog";

const SITE = "https://www.karzartools.com";
const PRODUCT_PAGE_SIZE = 1000;
/** Hard cap so a runaway API cannot blow sitemap generation. */
const MAX_PRODUCT_PAGES = 20;

async function collectProductEntries(
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
      entries.push({
        url: `${SITE}/product/${product.id}`,
        lastModified: now,
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
  now: Date,
): Promise<MetadataRoute.Sitemap> {
  try {
    const categories = await catalogService.listCategoriesFlat();
    return categories
      .filter((c) => (c.product_count ?? 0) > 0 && c.slug)
      .map((c) => ({
        url: `${SITE}/categories/${c.slug}`,
        lastModified: now,
        changeFrequency: "weekly" as const,
        priority: c.depth === 1 ? 0.85 : 0.7,
      }));
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticPaths = ["", "/catalog", "/blog", "/about", "/contact", "/terms", "/privacy"];

  const staticEntries: MetadataRoute.Sitemap = staticPaths.map((path) => ({
    url: `${SITE}${path || "/"}`,
    lastModified: now,
    changeFrequency: path === "" || path === "/catalog" ? "daily" : "weekly",
    priority: path === "" ? 1 : path === "/blog" ? 0.8 : 0.7,
  }));

  let blogEntries: MetadataRoute.Sitemap = [];
  try {
    const articles = await catalogService.listArticles();
    blogEntries = articles.map((a) => ({
      url: `${SITE}/blog/${a.slug}`,
      lastModified: a.published_at ? new Date(a.published_at) : now,
      changeFrequency: "monthly" as const,
      priority: 0.75,
    }));
  } catch {
    blogEntries = [];
  }

  let productEntries: MetadataRoute.Sitemap = [];
  try {
    productEntries = await collectProductEntries(now);
  } catch {
    productEntries = [];
  }

  const categoryEntries = await collectCategoryEntries(now);

  return [...staticEntries, ...categoryEntries, ...blogEntries, ...productEntries];
}
