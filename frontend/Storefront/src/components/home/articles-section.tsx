"use client";

import { useMemo } from "react";
import { ArticleCard, ArticleCardSkeleton } from "@/components/blog/article-card";
import { useArticles } from "@/features/catalog/queries";
import {
  sortArticlesByNewest,
  sortArticlesByViews,
} from "@/lib/articles";

const HOME_COUNT = 3;

export function ArticlesSection() {
  const { data, isLoading } = useArticles();

  const articles = useMemo(() => {
    const list = data ?? [];
    const byViews = sortArticlesByViews(list);
    if (byViews) return byViews.slice(0, HOME_COUNT);
    return sortArticlesByNewest(list).slice(0, HOME_COUNT);
  }, [data]);

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: HOME_COUNT }).map((_, i) => (
          <ArticleCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (articles.length === 0) return null;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-5">
      {articles.map((article, i) => (
        <ArticleCard
          key={article.id}
          article={article}
          index={i}
          priority={i < 2}
        />
      ))}
    </div>
  );
}
