/**
 * SEO Wave 1B: raw HTML crawl discovery + URL pagination contract.
 * Runs against production standalone build (see playwright.http-contract.config.ts).
 */
import { expect, test } from "@playwright/test";
const CATALOG_PAGE_SIZE = 20;

const BASE = process.env.HTTP_CONTRACT_BASE_URL ?? "http://127.0.0.1:3097";

async function fetchHtml(path: string): Promise<{ status: number; html: string }> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "User-Agent": "KarzarHttpContract/1b-crawl" },
  });
  return { status: res.status, html: await res.text() };
}

function extractHrefs(html: string, pattern: RegExp): string[] {
  const out: string[] = [];
  const re = new RegExp(pattern.source, pattern.flags.includes("g") ? pattern.flags : `${pattern.flags}g`);
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) {
    out.push(m[1] ?? m[0]);
  }
  return out;
}

function canonicalFromHtml(html: string): string | null {
  const m = html.match(/<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i)
    ?? html.match(/<link[^>]+href=["']([^"']+)["'][^>]+rel=["']canonical["']/i);
  if (!m) return null;
  try {
    const url = new URL(m[1], "https://www.karzartools.com");
    return `${url.pathname}${url.search}`;
  } catch {
    return m[1];
  }
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

test.describe("crawl discovery (raw HTML)", () => {
  test("/catalog exposes product and pagination links", async () => {
    const { status, html } = await fetchHtml("/catalog");
    expect(status).toBe(200);
    const products = productHrefs(html);
    expect(products.length).toBeGreaterThan(0);
    expect(products.length).toBeLessThanOrEqual(CATALOG_PAGE_SIZE);
    if (html.includes("page=2")) {
      expect(html).toMatch(/href=["'][^"']*\?page=2|href=["']\/catalog\?page=2/);
    }
    expect(canonicalFromHtml(html)).toBe("/catalog");
  });

  test("/catalog?page=2 serves page-two cohort with self canonical", async () => {
    const p1 = await fetchHtml("/catalog");
    if (!p1.html.includes("page=2")) {
      test.skip();
      return;
    }
    const p2 = await fetchHtml("/catalog?page=2");
    expect(p2.status).toBe(200);
    expect(canonicalFromHtml(p2.html)).toBe("/catalog?page=2");
    const products2 = productHrefs(p2.html);
    expect(products2.length).toBeGreaterThan(0);
    const products1 = productHrefs(p1.html);
    expect(products2.join(",")).not.toBe(products1.join(","));
    expect(p2.html).toMatch(/href=["']\/catalog["']/);
  });

  test("/catalog?page=999 → 404", async () => {
    const { status } = await fetchHtml("/catalog?page=999");
    expect(status).toBe(404);
  });

  test("category hub exposes product links", async () => {
    const { status, html } = await fetchHtml("/categories/kolis-mikrometr");
    expect(status).toBe(200);
    expect(productHrefs(html).length).toBeGreaterThan(0);
  });

  test("category hub page 2", async () => {
    const p1 = await fetchHtml("/categories/kolis-mikrometr");
    if (!p1.html.includes("page=2")) {
      test.skip();
      return;
    }
    const p2 = await fetchHtml("/categories/kolis-mikrometr?page=2");
    expect(p2.status).toBe(200);
    expect(canonicalFromHtml(p2.html)).toBe("/categories/kolis-mikrometr?page=2");
    const a = productHrefs(p1.html);
    const b = productHrefs(p2.html);
    expect(b.length).toBeGreaterThan(0);
    if (a.length > 0) {
      expect(b.join(",")).not.toBe(a.join(","));
    }
  });

  test("brand hub exposes product links", async () => {
    const { status, html } = await fetchHtml("/brands/bosch");
    expect(status).toBe(200);
    expect(productHrefs(html).length).toBeGreaterThan(0);
  });

  test("/categories index exposes category links", async () => {
    const { status, html } = await fetchHtml("/categories");
    expect(status).toBe(200);
    expect(categoryHrefs(html).length).toBeGreaterThan(0);
  });

  test("/blog exposes article links", async () => {
    const { status, html } = await fetchHtml("/blog");
    expect(status).toBe(200);
    expect(articleHrefs(html).length).toBeGreaterThan(0);
  });

  test("faceted catalog stays noindex with clean parent canonical", async () => {
    const { status, html } = await fetchHtml("/catalog?brand=1");
    expect(status).toBe(200);
    expect(html.toLowerCase()).toContain("noindex");
    expect(canonicalFromHtml(html)).toBe("/catalog");
  });
});
