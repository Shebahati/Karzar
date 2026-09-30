import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { BlogList } from "@/components/blog/blog-list";
import { catalogKeys } from "@/features/catalog/keys";
import { ARTICLES_PAGE_SIZE, sortArticlesByNewest } from "@/lib/articles";
import {
  INDEXABLE_STATIC_CANONICALS,
  selfCanonicalAlternates,
} from "@/lib/crawl-hygiene";
import { getQueryClient } from "@/lib/get-query-client";
import {
  isPageBeyondTotal,
  paginatedCanonicalPath,
  paginatedTitle,
  parsePageParam,
} from "@/lib/pagination-url";
import { redirectIfPageQueryNeedsNormalization } from "@/lib/pagination-request";
import { catalogService } from "@/services/catalog";

type SearchParams = Record<string, string | string[] | undefined>;

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}): Promise<Metadata> {
  const sp = await searchParams;
  const page = parsePageParam(sp.page);
  const baseTitle = "مجله کارزار";
  return {
    title: paginatedTitle(baseTitle, page),
    description: "مقالات تخصصی دنیای ابزار صنعتی و تراشکاری.",
    alternates: selfCanonicalAlternates(
      paginatedCanonicalPath(INDEXABLE_STATIC_CANONICALS.blog, page),
    ),
  };
}

export default async function BlogPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  redirectIfPageQueryNeedsNormalization("/blog", sp);
  const page = parsePageParam(sp.page);

  const queryClient = getQueryClient();
  const articles = await queryClient.fetchQuery({
    queryKey: catalogKeys.articles(),
    queryFn: () => catalogService.listArticles(),
  });

  const total = sortArticlesByNewest(articles).length;
  if (isPageBeyondTotal(page, total, ARTICLES_PAGE_SIZE)) {
    notFound();
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <BlogList initialArticles={articles} serverSearchParams={sp} />
    </HydrationBoundary>
  );
}
