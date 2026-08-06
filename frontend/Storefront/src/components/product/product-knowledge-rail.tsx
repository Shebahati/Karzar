"use client";

import { useMemo } from "react";
import { ArticleCard } from "@/components/blog/article-card";
import { SectionHeading } from "@/components/home/section-heading";
import { listBlogArticles } from "@/lib/blog-articles";
import type { Article } from "@/types/content";

/**
 * Read-only knowledge rail — articles that already assert a link to this product.
 * Hidden entirely when none exist (no invented content / empty spam).
 */
export function ProductKnowledgeRail({ productId }: { productId: number }) {
  const articles = useMemo(() => {
    if (!Number.isFinite(productId) || productId <= 0) return [] as Article[];
    return listBlogArticles()
      .filter(
        (a) =>
          a.is_published !== false &&
          Array.isArray(a.related_product_ids) &&
          a.related_product_ids.includes(productId),
      )
      .slice(0, 4)
      .map(
        (a, i): Article => ({
          id: 2000 + i,
          slug: a.slug,
          title: a.title,
          excerpt: a.excerpt,
          cover_image: a.cover_image,
          published_at: a.published_at,
          reading_minutes: a.reading_minutes,
          tags: a.tags,
        }),
      );
  }, [productId]);

  if (!articles.length) return null;

  return (
    <section className="mt-12 sm:mt-20" aria-labelledby="pdp-knowledge-heading">
      <SectionHeading
        id="pdp-knowledge-heading"
        title="دانش مرتبط"
        subtitle="راهنما و مقالات مرتبط با این محصول — فقط خواندنی"
        href="/blog"
        hrefLabel="مجله کارزار"
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {articles.map((article, index) => (
          <ArticleCard
            key={article.slug}
            article={article}
            variant="rail"
            index={index}
          />
        ))}
      </div>
    </section>
  );
}
