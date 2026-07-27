import { describe, expect, it } from "vitest";
import {
  articleBodyWordCount,
  articleHasFaq,
  articleHubLinks,
  getBlogArticle,
  listBlogArticles,
} from "@/lib/blog-articles";

const PRICE_STOCK_CLAIM =
  /(قیمت\s+\d|موجودی\s+(دارد|ندارد)|موجودی\s*انبار|در انبار است|تومان\b|ریال\b|\bIRR\b|\bstock\b|\bprice\s*\d)/i;

describe("SEO-003 buyer-intent articles", () => {
  const articles = listBlogArticles();

  it("ships exactly 24 unique calendar articles", () => {
    expect(articles).toHaveLength(24);
    expect(new Set(articles.map((a) => a.slug)).size).toBe(24);
    expect(new Set(articles.map((a) => a.calendar_id)).size).toBe(24);
    const expected = [
      "A01",
      "A02",
      "A03",
      "A04",
      "A05",
      "A06",
      "B01",
      "B02",
      "B03",
      "B04",
      "B05",
      "B06",
      "C01",
      "C02",
      "C03",
      "C04",
      "C05",
      "C06",
      "D01",
      "D02",
      "D03",
      "D04",
      "D05",
      "D06",
    ];
    expect(articles.map((a) => a.calendar_id)).toEqual(expected);
  });

  it("each article links ≥2 products, ≥1 hub, has FAQ, and readable body", () => {
    for (const article of articles) {
      expect(article.related_product_ids.length, article.slug).toBeGreaterThanOrEqual(2);
      expect(new Set(article.related_product_ids).size, article.slug).toBe(
        article.related_product_ids.length,
      );
      const hubs = articleHubLinks(article).filter((l) => l.href.startsWith("/categories/"));
      expect(hubs.length, article.slug).toBeGreaterThanOrEqual(1);
      expect(articleHasFaq(article), article.slug).toBe(true);
      // Mid-tail buyer guides: substantial body (not stubs), FAQ + links + products.
      expect(articleBodyWordCount(article), article.slug).toBeGreaterThanOrEqual(200);
      expect(article.excerpt.trim().length, article.slug).toBeGreaterThan(40);
      expect(article.blocks.some((b) => b.type === "meta"), article.slug).toBe(true);
    }
  });

  it("never claims price or stock in copy or link labels", () => {
    for (const article of articles) {
      const text = [
        article.title,
        article.excerpt,
        ...article.tags,
        ...article.blocks.flatMap((b) => {
          if (b.type === "meta") return [b.seo_title, b.seo_description];
          if (b.type === "paragraph" || b.type === "heading" || b.type === "subheading" || b.type === "callout")
            return [b.text];
          if (b.type === "list") return b.items;
          if (b.type === "faq") return b.items.flatMap((i) => [i.question, i.answer]);
          if (b.type === "links") return b.items.map((i) => i.label);
          if (b.type === "table") return [...b.headers, ...b.rows.flat()];
          return [];
        }),
      ].join("\n");
      expect(PRICE_STOCK_CLAIM.test(text), article.slug).toBe(false);
    }
  });

  it("resolves known calendar slugs", () => {
    expect(getBlogArticle("digital-caliper-workshop-accuracy")?.calendar_id).toBe("A01");
    expect(getBlogArticle("case-study-scrap-reduction-dimensional-control")?.calendar_id).toBe(
      "D06",
    );
    expect(getBlogArticle("missing-slug-xyz")).toBeNull();
  });
});
