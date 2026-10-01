/**
 * SEO Wave 1C: production standalone sitemap index + child sitemaps.
 */
import { expect, test } from "@playwright/test";

const SITE = "https://www.karzartools.com";

async function fetchText(
  baseURL: string,
  path: string,
): Promise<{ status: number; text: string; type: string | null }> {
  const origin = baseURL.replace(/\/$/, "");
  const res = await fetch(`${origin}${path}`, {
    headers: { "User-Agent": "KarzarHttpContract/1c-sitemap" },
  });
  return {
    status: res.status,
    text: await res.text(),
    type: res.headers.get("content-type"),
  };
}

function locs(xml: string): string[] {
  const out: string[] = [];
  const re = /<loc>([^<]+)<\/loc>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(xml)) !== null) {
    out.push(m[1]!);
  }
  return out;
}

test.describe("sitemap contract (production standalone)", () => {
  test("GET /sitemap.xml is sitemap index", async ({ baseURL }) => {
    const { status, text, type } = await fetchText(baseURL!, "/sitemap.xml");
    expect(status).toBe(200);
    expect(type ?? "").toMatch(/xml/);
    expect(text).toContain("<sitemapindex");
    expect(text).not.toContain("<urlset");
    const childLocs = locs(text);
    expect(childLocs).toContain(`${SITE}/sitemaps/static.xml`);
    expect(childLocs).toContain(`${SITE}/sitemaps/categories.xml`);
    expect(childLocs).toContain(`${SITE}/sitemaps/brands.xml`);
    expect(childLocs).toContain(`${SITE}/sitemaps/blog.xml`);
    const productShards = childLocs.filter((l) => l.includes("/sitemaps/products/"));
    expect(productShards.length).toBeGreaterThan(0);
    expect(new Set(childLocs).size).toBe(childLocs.length);
  });

  test("child sitemaps return urlset", async ({ baseURL }) => {
    const paths = [
      "/sitemaps/static.xml",
      "/sitemaps/categories.xml",
      "/sitemaps/brands.xml",
      "/sitemaps/blog.xml",
      "/sitemaps/products/0.xml",
    ];
    for (const path of paths) {
      const { status, text, type } = await fetchText(baseURL!, path);
      expect(status).toBe(200);
      expect(type ?? "").toMatch(/xml/);
      expect(text).toContain("<urlset");
    }
  });

  test("static sitemap includes /categories", async ({ baseURL }) => {
    const { text } = await fetchText(baseURL!, "/sitemaps/static.xml");
    expect(locs(text)).toContain(`${SITE}/categories`);
    expect(locs(text)).toContain(`${SITE}/catalog`);
  });

  test("product shard uses canonical slug URLs", async ({ baseURL }) => {
    const { text } = await fetchText(baseURL!, "/sitemaps/products/0.xml");
    const productLocs = locs(text);
    expect(productLocs.length).toBeGreaterThan(0);
    expect(productLocs.some((l) => l.includes("/product/"))).toBe(true);
    expect(productLocs.some((l) => /\/product\/\d+$/.test(l))).toBe(false);
  });

  test("no facet or pagination URLs in sitemaps", async ({ baseURL }) => {
    const { text: index } = await fetchText(baseURL!, "/sitemap.xml");
    const { text: products } = await fetchText(baseURL!, "/sitemaps/products/0.xml");
    const all = index + products;
    expect(all).not.toMatch(/\?page=/);
    expect(all).not.toMatch(/\?brand=/);
    expect(all).not.toMatch(/\?search=/);
  });

  test("invalid product shard returns 404", async ({ baseURL }) => {
    const { status } = await fetchText(baseURL!, "/sitemaps/products/99999.xml");
    expect(status).toBe(404);
  });

  test("route collision: categories sitemap is XML not category page", async ({ baseURL }) => {
    const { status, text, type } = await fetchText(baseURL!, "/sitemaps/categories.xml");
    expect(status).toBe(200);
    expect(type ?? "").toMatch(/xml/);
    expect(text).toContain("<urlset");
  });

  test("entity pages still resolve", async ({ baseURL }) => {
    const product = await fetchText(baseURL!, "/product/bsh-gsb-13re");
    expect(product.status).toBe(200);
    const category = await fetchText(baseURL!, "/categories/kolis-mikrometr");
    expect(category.status).toBe(200);
    const brand = await fetchText(baseURL!, "/brands/bosch");
    expect(brand.status).toBe(200);
    const article = await fetchText(baseURL!, "/blog/how-to-choose-drill");
    expect(article.status).toBe(200);
  });
});
