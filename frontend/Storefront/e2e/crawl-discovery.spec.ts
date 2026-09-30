/**
 * SEO Wave 1B: raw HTML crawl discovery + URL pagination contract.
 * Runs against production standalone build (playwright.http-contract.config.ts).
 */
import { expect, test } from "@playwright/test";

const CATALOG_PAGE_SIZE = 20;
const BASE = process.env.HTTP_CONTRACT_BASE_URL ?? "http://127.0.0.1:3097";

const CATEGORY_SLUG = "kolis-mikrometr";
const BRAND_SLUG = "bosch";
/** Deterministic public-unavailable SKU in base mock (`MKT-9555` → slug). */
const OOS_PRODUCT_SLUG = "mkt-9555";

async function fetchHtml(path: string): Promise<{ status: number; html: string }> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "User-Agent": "KarzarHttpContract/1b-crawl" },
  });
  return { status: res.status, html: await res.text() };
}

async function fetchRedirect(path: string): Promise<{ status: number; location: string | null }> {
  const res = await fetch(`${BASE}${path}`, {
    redirect: "manual",
    headers: { "User-Agent": "KarzarHttpContract/1b-crawl" },
  });
  return { status: res.status, location: res.headers.get("location") };
}

function extractHrefs(html: string, pattern: RegExp): string[] {
  const out: string[] = [];
  const re = new RegExp(
    pattern.source,
    pattern.flags.includes("g") ? pattern.flags : `${pattern.flags}g`,
  );
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) {
    out.push(m[1] ?? m[0]);
  }
  return out;
}

function canonicalFromHtml(html: string): string | null {
  const m =
    html.match(/<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i) ??
    html.match(/<link[^>]+href=["']([^"']+)["'][^>]+rel=["']canonical["']/i);
  if (!m) return null;
  try {
    const url = new URL(m[1], "https://www.karzartools.com");
    return `${url.pathname}${url.search}`;
  } catch {
    return m[1];
  }
}

function robotsFromHtml(html: string): string {
  const m = html.match(/<meta[^>]+name=["']robots["'][^>]+content=["']([^"']+)["']/i);
  return (m?.[1] ?? "").toLowerCase();
}

function productHrefs(html: string): string[] {
  return extractHrefs(html, /href=["'](\/product\/[^"'#?]+)["']/gi);
}

function categoryHrefs(html: string): string[] {
  return extractHrefs(html, /href=["'](\/categories\/[^"'#?]+)["']/gi);
}

function articleHrefs(html: string): string[] {
  return extractHrefs(html, /href=["'](\/blog\/[^"'#?]+)["']/gi);
}

function expectPage2Link(html: string, pathPrefix: string): void {
  expect(html).toMatch(
    new RegExp(`href=["']${pathPrefix.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(\\?[^"']*)?page=2`),
  );
}

test.describe("crawl discovery (raw HTML)", () => {
  test("catalog page 1", async () => {
    const { status, html } = await fetchHtml("/catalog");
    expect(status).toBe(200);
    const products = productHrefs(html);
    expect(products.length).toBeGreaterThan(0);
    expect(products.length).toBeLessThanOrEqual(CATALOG_PAGE_SIZE);
    expectPage2Link(html, "/catalog");
    expect(canonicalFromHtml(html)).toBe("/catalog");
  });

  test("catalog page 2", async () => {
    const p1 = await fetchHtml("/catalog");
    const p2 = await fetchHtml("/catalog?page=2");
    expect(p2.status).toBe(200);
    expect(canonicalFromHtml(p2.html)).toBe("/catalog?page=2");
    const products1 = productHrefs(p1.html);
    const products2 = productHrefs(p2.html);
    expect(products2.length).toBeGreaterThan(0);
    expect(products2.length).toBeLessThanOrEqual(CATALOG_PAGE_SIZE);
    expect(products2.join(",")).not.toBe(products1.join(","));
    expect(p2.html).toMatch(/href=["']\/catalog["']/);
  });

  test("category hub page 1", async () => {
    const { status, html } = await fetchHtml(`/categories/${CATEGORY_SLUG}`);
    expect(status).toBe(200);
    expect(productHrefs(html).length).toBeGreaterThan(0);
    expectPage2Link(html, `/categories/${CATEGORY_SLUG}`);
  });

  test("category hub page 2", async () => {
    const p1 = await fetchHtml(`/categories/${CATEGORY_SLUG}`);
    const p2 = await fetchHtml(`/categories/${CATEGORY_SLUG}?page=2`);
    expect(p2.status).toBe(200);
    expect(canonicalFromHtml(p2.html)).toBe(`/categories/${CATEGORY_SLUG}?page=2`);
    const a = productHrefs(p1.html);
    const b = productHrefs(p2.html);
    expect(b.length).toBeGreaterThan(0);
    expect(b.join(",")).not.toBe(a.join(","));
  });

  test("brand hub page 1", async () => {
    const { status, html } = await fetchHtml(`/brands/${BRAND_SLUG}`);
    expect(status).toBe(200);
    expect(productHrefs(html).length).toBeGreaterThan(0);
    expectPage2Link(html, `/brands/${BRAND_SLUG}`);
  });

  test("brand hub page 2", async () => {
    const p1 = await fetchHtml(`/brands/${BRAND_SLUG}`);
    const p2 = await fetchHtml(`/brands/${BRAND_SLUG}?page=2`);
    expect(p2.status).toBe(200);
    expect(canonicalFromHtml(p2.html)).toBe(`/brands/${BRAND_SLUG}?page=2`);
    const a = productHrefs(p1.html);
    const b = productHrefs(p2.html);
    expect(b.length).toBeGreaterThan(0);
    expect(b.join(",")).not.toBe(a.join(","));
  });

  test("blog page 1", async () => {
    const { status, html } = await fetchHtml("/blog");
    expect(status).toBe(200);
    expect(articleHrefs(html).length).toBeGreaterThan(0);
    expectPage2Link(html, "/blog");
  });

  test("blog page 2", async () => {
    const p1 = await fetchHtml("/blog");
    const p2 = await fetchHtml("/blog?page=2");
    expect(p2.status).toBe(200);
    expect(canonicalFromHtml(p2.html)).toBe("/blog?page=2");
    const a = articleHrefs(p1.html);
    const b = articleHrefs(p2.html);
    expect(b.length).toBeGreaterThan(0);
    expect(b.join(",")).not.toBe(a.join(","));
  });

  test("/categories index exposes category links", async () => {
    const { status, html } = await fetchHtml("/categories");
    expect(status).toBe(200);
    expect(categoryHrefs(html).length).toBeGreaterThan(0);
  });

  test("out-of-range pagination → 404", async () => {
    const routes = [
      "/catalog?page=999",
      `/categories/${CATEGORY_SLUG}?page=999`,
      `/brands/${BRAND_SLUG}?page=999`,
      "/blog?page=999",
    ];
    for (const path of routes) {
      const { status } = await fetchHtml(path);
      expect(status).toBe(404);
    }
  });

  test("page=1 normalization redirects to clean URL", async () => {
    const cases = [
      { raw: "/catalog?page=1", clean: "/catalog" },
      { raw: `/categories/${CATEGORY_SLUG}?page=1`, clean: `/categories/${CATEGORY_SLUG}` },
      { raw: `/brands/${BRAND_SLUG}?page=1`, clean: `/brands/${BRAND_SLUG}` },
      { raw: "/blog?page=1", clean: "/blog" },
    ];
    for (const { raw, clean } of cases) {
      const { status, location } = await fetchRedirect(raw);
      expect([301, 302, 307, 308]).toContain(status);
      expect(location).toMatch(new RegExp(`${clean.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`));
    }
  });

  test("faceted catalog page 2 preserves facet and noindex", async () => {
    const { status, html } = await fetchHtml("/catalog?brand=1&page=2");
    expect(status).toBe(200);
    expect(robotsFromHtml(html)).toContain("noindex");
    expect(canonicalFromHtml(html)).toBe("/catalog");
    expect(productHrefs(html).length).toBeGreaterThan(0);
    expect(html).toContain("brand=1");
    expect(html).toMatch(/page=3|page=1|\/catalog\?brand=1/);
    const p1 = await fetchHtml("/catalog?brand=1");
    const p2 = productHrefs(html);
    const p1h = productHrefs(p1.html);
    if (p1h.length > 0 && p2.length > 0) {
      expect(p2.join(",")).not.toBe(p1h.join(","));
    }
  });

  test("public unavailable product remains discoverable and OutOfStock on PDP", async () => {
    let discovered = false;
    for (const page of [1, 2, 3] as const) {
      const path = page === 1 ? "/catalog" : `/catalog?page=${page}`;
      const { status, html } = await fetchHtml(path);
      expect(status).toBe(200);
      if (productHrefs(html).some((h) => h.includes(OOS_PRODUCT_SLUG))) {
        discovered = true;
        break;
      }
    }
    expect(discovered).toBe(true);
    const pdp = await fetchHtml(`/product/${OOS_PRODUCT_SLUG}`);
    expect(pdp.status).toBe(200);
    expect(pdp.html).toMatch(/OutOfStock/i);
  });
});
