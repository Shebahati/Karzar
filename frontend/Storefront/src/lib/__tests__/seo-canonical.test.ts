import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { metadata as aboutMetadata } from "@/app/about/page";
import { metadata as accountMetadata } from "@/app/account/layout";
import { metadata as blogMetadata } from "@/app/blog/page";
import { generateMetadata as catalogMetadata } from "@/app/catalog/page";
import { metadata as categoriesMetadata } from "@/app/categories/page";
import { metadata as checkoutMetadata } from "@/app/checkout/layout";
import { metadata as contactMetadata } from "@/app/contact/page";
import { metadata as faqMetadata } from "@/app/faq/page";
import { metadata as loginMetadata } from "@/app/login/page";
import { metadata as homeMetadata } from "@/app/page";
import { metadata as quoteMetadata } from "@/app/quote/page";
import { metadata as termsMetadata } from "@/app/terms/page";
import { metadata as cartMetadata } from "@/app/cart/page";
import {
  INDEXABLE_STATIC_CANONICALS,
  NOINDEX_FOLLOW,
  NOINDEX_NOFOLLOW,
  ROBOTS_DISALLOW,
  SITEMAP_STATIC_PATHS,
} from "@/lib/crawl-hygiene";
import { productPath } from "@/lib/product-url";
import { DEFAULT_SITE_URL } from "@/lib/site-url";

function layoutSource(): string {
  return readFileSync(
    path.resolve(__dirname, "../../app/layout.tsx"),
    "utf8",
  );
}

function absoluteCanonical(pathname: string): string {
  return new URL(pathname, DEFAULT_SITE_URL).href;
}

describe("root canonical inheritance", () => {
  it("does not impose homepage canonical on all routes", () => {
    const src = layoutSource();
    expect(src).toContain("metadataBase");
    expect(src).not.toMatch(/alternates\s*:\s*\{[\s\S]*canonical\s*:/);
    expect(src).not.toMatch(/canonical\s*:\s*SITE_URL/);
  });

  it("homepage self-canonical resolves to the production origin slash", () => {
    expect(homeMetadata.alternates?.canonical).toBe(
      INDEXABLE_STATIC_CANONICALS.home,
    );
    expect(absoluteCanonical(INDEXABLE_STATIC_CANONICALS.home)).toBe(
      "https://www.karzartools.com/",
    );
  });
});

describe("static indexable self-canonicals", () => {
  const pages: Array<{ path: string; canonical: unknown }> = [
    { path: "/", canonical: homeMetadata.alternates?.canonical },
    { path: "/about", canonical: aboutMetadata.alternates?.canonical },
    { path: "/contact", canonical: contactMetadata.alternates?.canonical },
    { path: "/terms", canonical: termsMetadata.alternates?.canonical },
    { path: "/faq", canonical: faqMetadata.alternates?.canonical },
    { path: "/blog", canonical: blogMetadata.alternates?.canonical },
    { path: "/categories", canonical: categoriesMetadata.alternates?.canonical },
  ];

  it.each(pages)("$path declares its own canonical, not the homepage", ({ path: route, canonical }) => {
    expect(canonical).toBe(route);
    if (route !== "/") {
      expect(canonical).not.toBe("/");
      expect(canonical).not.toBe(DEFAULT_SITE_URL);
    }
    expect(absoluteCanonical(String(canonical))).toBe(
      `${DEFAULT_SITE_URL}${route === "/" ? "/" : route}`,
    );
  });
});

describe("catalog crawl hygiene", () => {
  it("keeps clean /catalog indexable with self canonical", async () => {
    const meta = await catalogMetadata({ searchParams: Promise.resolve({}) });
    expect(meta.alternates?.canonical).toBe(INDEXABLE_STATIC_CANONICALS.catalog);
    expect(meta.robots).toBeUndefined();
  });

  it("keeps faceted catalog noindex,follow with clean parent canonical", async () => {
    const meta = await catalogMetadata({
      searchParams: Promise.resolve({ brand: "1", sort: "newest" }),
    });
    expect(meta.robots).toEqual(NOINDEX_FOLLOW);
    expect(meta.alternates?.canonical).toBe("/catalog");
  });
});

describe("private routes", () => {
  it("remain noindex", () => {
    expect(loginMetadata.robots).toEqual(NOINDEX_NOFOLLOW);
    expect(cartMetadata.robots).toEqual(NOINDEX_NOFOLLOW);
    expect(quoteMetadata.robots).toEqual(NOINDEX_NOFOLLOW);
    expect(accountMetadata.robots).toEqual(NOINDEX_NOFOLLOW);
    expect(checkoutMetadata.robots).toEqual(NOINDEX_NOFOLLOW);
  });

  it("are disallowed in robots.txt policy", () => {
    expect([...ROBOTS_DISALLOW]).toEqual(
      expect.arrayContaining(["/login", "/cart", "/quote", "/account/", "/checkout/"]),
    );
  });
});

describe("product + sitemap URL hygiene", () => {
  it("slug PDP canonical is the slug path, not numeric id", () => {
    expect(
      productPath({ id: 7115, slug: "digital-caliper" }),
    ).toBe("/product/digital-caliper");
    expect(productPath({ id: 7115, slug: "کولیس-دیجیتال" })).toBe(
      "/product/کولیس-دیجیتال",
    );
  });

  it("sitemap uses slug URL when slug exists and never a numeric twin", () => {
    const site = DEFAULT_SITE_URL;
    const withSlug = { id: 7115, slug: "digital-caliper" };
    const slugUrl = `${site}${productPath(withSlug)}`;
    expect(slugUrl).toBe("https://www.karzartools.com/product/digital-caliper");
    expect(slugUrl).not.toContain("/product/7115");
    expect(`${site}${productPath({ id: 7115, slug: null })}`).toBe(
      "https://www.karzartools.com/product/7115",
    );
  });

  it("static sitemap set is deterministic and excludes faceted/private URLs", () => {
    expect([...SITEMAP_STATIC_PATHS]).toEqual([
      "/",
      "/catalog",
      "/blog",
      "/about",
      "/contact",
      "/terms",
      "/faq",
    ]);
    expect(SITEMAP_STATIC_PATHS.some((p) => p.includes("?"))).toBe(false);
    expect(SITEMAP_STATIC_PATHS).not.toContain("/login");
    expect(SITEMAP_STATIC_PATHS).not.toContain("/cart");
  });
});
