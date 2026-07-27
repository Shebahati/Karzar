/**
 * SEO-003 — buyer-intent blog articles (calendar A01–D06).
 * Source: content/blog/articles.json (bundled at build time for tests + mock).
 */

import articlesJson from "../../content/blog/articles.json";
import type { BlogBlock, BlogPost } from "@/types/content";

export type BlogArticleSource = {
  calendar_id: string;
  slug: string;
  title: string;
  excerpt: string;
  cover_image: string;
  published_at: string;
  reading_minutes: number;
  author: string;
  tags: string[];
  related_product_ids: number[];
  related_product_queries?: string[];
  is_published?: boolean;
  blocks: BlogBlock[];
};

type BlogArticlesFile = {
  version: number;
  task: string;
  count: number;
  articles: BlogArticleSource[];
};

const DATA = articlesJson as BlogArticlesFile;

const BY_SLUG = new Map(DATA.articles.map((a) => [a.slug, a]));

/** Count whitespace-separated tokens (Persian/Latin). */
export function countWords(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).filter(Boolean).length;
}

export function articleBodyWordCount(article: BlogArticleSource): number {
  const parts: string[] = [];
  for (const block of article.blocks) {
    if (block.type === "meta") continue;
    if ("text" in block && typeof block.text === "string") parts.push(block.text);
    if (block.type === "list") parts.push(...block.items);
    if (block.type === "faq") {
      for (const item of block.items) {
        parts.push(item.question, item.answer);
      }
    }
    if (block.type === "links") {
      parts.push(...block.items.map((i) => i.label));
    }
    if (block.type === "table") {
      parts.push(...block.headers, ...block.rows.flat());
    }
  }
  return countWords(parts.join(" "));
}

export function listBlogArticles(): BlogArticleSource[] {
  return DATA.articles;
}

export function getBlogArticle(slug: string | null | undefined): BlogArticleSource | null {
  if (!slug) return null;
  return BY_SLUG.get(slug) ?? null;
}

export function blogArticleToPost(article: BlogArticleSource, id: number): BlogPost {
  return {
    id,
    slug: article.slug,
    title: article.title,
    excerpt: article.excerpt,
    cover_image: article.cover_image,
    published_at: article.published_at,
    reading_minutes: article.reading_minutes,
    author: article.author,
    tags: article.tags,
    related_product_ids: article.related_product_ids,
    blocks: article.blocks,
  };
}

/** Internal /categories or /blog links from links blocks. */
export function articleHubLinks(article: BlogArticleSource): { href: string; label: string }[] {
  const out: { href: string; label: string }[] = [];
  for (const block of article.blocks) {
    if (block.type !== "links") continue;
    for (const item of block.items) {
      if (item.href.startsWith("/categories/") || item.href.startsWith("/blog")) {
        out.push(item);
      }
    }
  }
  return out;
}

export function articleHasFaq(article: BlogArticleSource): boolean {
  return article.blocks.some((b) => b.type === "faq");
}
