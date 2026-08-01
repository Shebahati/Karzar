import type { Article } from "@/types/content";

/** Soft category label from the first tag when present. */
export function articleCategory(article: Article): string | null {
  const tag = article.tags?.find((t) => Boolean(t?.trim()));
  return tag?.trim() || null;
}

export function sortArticlesByNewest(articles: Article[]): Article[] {
  return [...articles].sort(
    (a, b) =>
      new Date(b.published_at).getTime() - new Date(a.published_at).getTime(),
  );
}

/**
 * Sort by views when the API payload already includes `views`.
 * Returns null when no article has views — callers must not invent ranking.
 */
export function sortArticlesByViews(articles: Article[]): Article[] | null {
  const hasViews = articles.some(
    (a) => typeof a.views === "number" && Number.isFinite(a.views),
  );
  if (!hasViews) return null;
  return [...articles].sort((a, b) => (b.views ?? 0) - (a.views ?? 0));
}

export type ArticleCategoryGroup = {
  label: string;
  articles: Article[];
};

/** Group by first tag; thin/empty tags → empty list (callers skip the section). */
export function groupArticlesByCategory(
  articles: Article[],
  { minPerGroup = 1, maxGroups = 8 }: { minPerGroup?: number; maxGroups?: number } = {},
): ArticleCategoryGroup[] {
  const map = new Map<string, Article[]>();
  for (const article of articles) {
    const label = articleCategory(article);
    if (!label) continue;
    const bucket = map.get(label);
    if (bucket) bucket.push(article);
    else map.set(label, [article]);
  }
  return [...map.entries()]
    .map(([label, items]) => ({
      label,
      articles: sortArticlesByNewest(items),
    }))
    .filter((g) => g.articles.length >= minPerGroup)
    .sort((a, b) => b.articles.length - a.articles.length || a.label.localeCompare(b.label, "fa"))
    .slice(0, maxGroups);
}

export const ARTICLES_PAGE_SIZE = 20;

export function paginateArticles(
  articles: Article[],
  page: number,
  pageSize = ARTICLES_PAGE_SIZE,
): { items: Article[]; page: number; totalPages: number; total: number } {
  const total = articles.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize) || 1);
  const safePage = Math.min(Math.max(1, page), totalPages);
  const start = (safePage - 1) * pageSize;
  return {
    items: articles.slice(start, start + pageSize),
    page: safePage,
    totalPages,
    total,
  };
}
