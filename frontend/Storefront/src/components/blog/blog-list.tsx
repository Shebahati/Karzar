"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { searchParamsToUrlSearchParams } from "@/lib/pagination-request";
import { AnimatePresence, motion } from "framer-motion";
import { ArticleCard, ArticleCardSkeleton } from "@/components/blog/article-card";
import { SectionHeading } from "@/components/home/section-heading";
import { AutoCarousel } from "@/components/ui/auto-carousel";
import { Container } from "@/components/ui/container";
import { PaginationNav } from "@/components/ui/pagination-nav";
import { useArticles } from "@/features/catalog/queries";
import {
  ARTICLES_PAGE_SIZE,
  groupArticlesByCategory,
  paginateArticles,
  sortArticlesByNewest,
  sortArticlesByViews,
} from "@/lib/articles";
import { buildPaginatedHref, parsePageParam } from "@/lib/pagination-url";
import { cn, formatNumber } from "@/lib/utils";
import type { Article } from "@/types/content";

function MagazineCategoryTabs({
  groups,
}: {
  groups: { label: string; articles: Article[] }[];
}) {
  const [selected, setSelected] = useState(groups[0]?.label ?? "");

  useEffect(() => {
    if (!groups.some((g) => g.label === selected)) {
      setSelected(groups[0]?.label ?? "");
    }
  }, [groups, selected]);

  const active = groups.find((g) => g.label === selected) ?? groups[0];
  if (!active) return null;

  const articles = active.articles;
  const useRail = articles.length > 4;

  return (
    <section aria-labelledby="magazine-topics-heading" className="space-y-4 sm:space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="h-6 w-1.5 rounded-full bg-[#D02327]" aria-hidden />
            <h2 id="magazine-topics-heading" className="type-section text-foreground">
              موضوعات مجله
            </h2>
          </div>
          <p className="type-lede mt-1.5 ps-4 text-[#5E5F5E]">
            موضوع را انتخاب کنید و مقالات همان دسته را ببینید
          </p>
        </div>
        <p className="ps-4 text-[11px] font-bold text-[#5E5F5E]/70 sm:ps-0">
          {formatNumber(articles.length)} مقاله در «{active.label}»
        </p>
      </div>

      <div
        role="tablist"
        aria-label="موضوعات مجله"
        className="relative no-scrollbar h-scroll flex gap-1 pb-1"
      >
        <div className="flex min-w-full gap-1 border-b border-[#5E5F5E]/12 sm:flex-wrap sm:overflow-visible">
          {groups.map((group) => {
            const isActive = group.label === active.label;
            return (
              <button
                key={group.label}
                type="button"
                role="tab"
                aria-selected={isActive}
                id={`mag-tab-${group.label}`}
                aria-controls="magazine-topic-panel"
                onClick={() => setSelected(group.label)}
                className={cn(
                  "relative shrink-0 px-3.5 py-2.5 text-sm font-bold transition-colors duration-200",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/35 focus-visible:ring-offset-2",
                  isActive ? "text-[#D02327]" : "text-[#5E5F5E] hover:text-foreground",
                )}
              >
                <span className="inline-flex items-center gap-1.5">
                  {group.label}
                  <span
                    className={cn(
                      "rounded-md px-1.5 py-0.5 text-[10px] font-bold tabular-nums",
                      isActive
                        ? "bg-[#D02327]/[0.1] text-[#D02327]"
                        : "bg-[#5E5F5E]/[0.08] text-[#5E5F5E]/80",
                    )}
                  >
                    {formatNumber(group.articles.length)}
                  </span>
                </span>
                {isActive ? (
                  <motion.span
                    layoutId="magazine-tab-indicator"
                    className="absolute inset-x-2 -bottom-px h-[2.5px] rounded-full bg-[#D02327]"
                    transition={{ type: "spring", stiffness: 420, damping: 32 }}
                  />
                ) : null}
              </button>
            );
          })}
        </div>
      </div>

      <div
        role="tabpanel"
        id="magazine-topic-panel"
        aria-labelledby={`mag-tab-${active.label}`}
        className="relative"
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={active.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.28, ease: "easeOut" }}
          >
            {useRail ? (
              <div className="rounded-[1.25rem] bg-gradient-to-l from-[#5E5F5E]/[0.04] via-transparent to-[#D02327]/[0.04] p-1 sm:p-2">
                <AutoCarousel
                  autoPlay={articles.length > 3}
                  intervalMs={3800}
                  itemClassName="w-[200px] sm:w-[230px]"
                  gapClass="gap-3"
                  trackClassName="pb-1"
                  showControls={articles.length > 3}
                >
                  {articles.map((article, i) => (
                    <ArticleCard
                      key={`${active.label}-${article.id}`}
                      article={article}
                      variant="rail"
                      index={i}
                    />
                  ))}
                </AutoCarousel>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2 sm:gap-2.5 md:grid-cols-3 lg:grid-cols-4">
                {articles.map((article, i) => (
                  <ArticleCard
                    key={`${active.label}-${article.id}`}
                    article={article}
                    variant="tile"
                    index={i}
                  />
                ))}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}

type ServerSearchParams = Record<string, string | string[] | undefined>;

export function BlogList({
  initialArticles,
  serverSearchParams = {},
}: {
  initialArticles?: Article[];
  serverSearchParams?: ServerSearchParams;
} = {}) {
  const { data, isLoading } = useArticles(initialArticles);
  const pathname = usePathname();
  const searchParams = useMemo(
    () => searchParamsToUrlSearchParams(serverSearchParams),
    [serverSearchParams],
  );

  const pageFromUrl = parsePageParam(searchParams.get("page") ?? undefined);

  const resolved = data ?? initialArticles ?? [];

  const newest = useMemo(
    () => sortArticlesByNewest(resolved),
    [resolved],
  );

  const mostViewedSorted = useMemo(
    () => sortArticlesByViews(resolved),
    [resolved],
  );

  const mostViewed = useMemo(() => {
    if (mostViewedSorted) return mostViewedSorted.slice(0, 8);
    // No views in API — complementary strip after the asymmetric newest block.
    return newest.slice(3, 11);
  }, [mostViewedSorted, newest]);

  const categoryGroups = useMemo(
    () => groupArticlesByCategory(resolved, { minPerGroup: 1, maxGroups: 6 }),
    [resolved],
  );

  const allSorted = newest;
  const { items: pageItems, page, totalPages, total } = paginateArticles(
    allSorted,
    pageFromUrl,
    ARTICLES_PAGE_SIZE,
  );

  const hrefForPage = useCallback(
    (target: number) => buildPaginatedHref(pathname, searchParams, target),
    [pathname, searchParams],
  );

  const showLoading = isLoading && initialArticles === undefined;

  const featured = newest[0];
  const sideNewest = newest.slice(1, 3);
  const restNewest = newest.slice(3, 6);

  return (
    <div className="relative overflow-hidden bg-hero-glow">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          backgroundImage:
            "radial-gradient(ellipse 70% 40% at 100% -10%, rgba(208,35,39,0.07), transparent), radial-gradient(ellipse 50% 35% at 0% 20%, rgba(94,95,94,0.06), transparent)",
        }}
      />

      <Container className="space-y-8 py-6 sm:space-y-10 sm:py-8 lg:space-y-14 lg:py-12">
        <header className="mx-auto max-w-2xl text-center">
          <span className="inline-block rounded-full bg-[#D02327]/[0.08] px-3 py-1 text-xs font-bold text-[#D02327]">
            مجله کارزار
          </span>
          <h1 className="mt-2.5 text-2xl font-bold text-foreground sm:mt-3 sm:text-4xl">
            دانش، راهنما و دنیای ابزار
          </h1>
          <p className="mx-auto mt-1.5 max-w-md text-sm leading-6 text-[#5E5F5E] sm:mt-2">
            جدیدترین مقالات تخصصی برای انتخاب و نگهداری بهتر ابزارها
          </p>
        </header>

        {/* A. Newest — asymmetric, compact */}
        <section aria-labelledby="newest-articles-heading">
          <SectionHeading
            id="newest-articles-heading"
            title="جدیدترین‌ها"
            subtitle="تازه‌ترین راهنماها و نکات فنی"
          />
          {showLoading ? (
            <div className="grid gap-3 lg:grid-cols-12 lg:gap-3.5">
              <ArticleCardSkeleton variant="featured" className="lg:col-span-7" />
              <div className="grid gap-3 lg:col-span-5">
                <ArticleCardSkeleton variant="side" />
                <ArticleCardSkeleton variant="side" />
              </div>
            </div>
          ) : newest.length === 0 ? (
            <p className="rounded-2xl bg-card px-5 py-10 text-center text-sm text-[#5E5F5E]">
              هنوز مقاله‌ای منتشر نشده است.
            </p>
          ) : (
            <div className="space-y-3">
              <div className="grid gap-3 lg:grid-cols-12 lg:gap-3.5">
                {featured ? (
                  <div className="lg:col-span-7">
                    <ArticleCard article={featured} variant="featured" priority />
                  </div>
                ) : null}
                <div className="grid gap-3 sm:grid-cols-2 lg:col-span-5 lg:grid-cols-1">
                  {sideNewest.map((article, i) => (
                    <ArticleCard
                      key={article.id}
                      article={article}
                      variant="side"
                      index={i}
                    />
                  ))}
                </div>
              </div>
              {/* Mobile: lead + 2 side only; bottom 3 from md+ */}
              {restNewest.length > 0 ? (
                <div className="hidden gap-2.5 md:grid md:grid-cols-2 lg:grid-cols-3 lg:gap-3">
                  {restNewest.map((article, i) => (
                    <ArticleCard
                      key={article.id}
                      article={article}
                      variant="tile"
                      index={i + 2}
                    />
                  ))}
                </div>
              ) : null}
            </div>
          )}
        </section>

        {/* B. Most viewed — desktop only */}
        {!showLoading && mostViewed.length > 0 ? (
          <section
            aria-labelledby="most-viewed-heading"
            className="hidden md:block"
          >
            <SectionHeading
              id="most-viewed-heading"
              title="پربازدید"
              subtitle={
                mostViewedSorted
                  ? "مرتب‌شده بر اساس بازدید"
                  : "منتخب خواندنی‌های مجله"
              }
            />
            <div className="rounded-[1.25rem] border border-[#D02327]/10 bg-[linear-gradient(120deg,rgba(208,35,39,0.04),rgba(94,95,94,0.05))] p-2.5 sm:p-3">
              <AutoCarousel
                autoPlay={mostViewed.length > 2}
                intervalMs={3600}
                itemClassName="w-[200px] sm:w-[230px]"
                gapClass="gap-3"
                trackClassName="pb-1"
                showControls={mostViewed.length > 2}
              >
                {mostViewed.map((article, i) => (
                  <ArticleCard
                    key={`mv-${article.id}`}
                    article={article}
                    variant="rail"
                    index={i}
                  />
                ))}
              </AutoCarousel>
            </div>
          </section>
        ) : null}

        {/* C. Magazine topics — selectable tabs */}
        {!showLoading && categoryGroups.length > 0 ? (
          <MagazineCategoryTabs groups={categoryGroups} />
        ) : null}

        {/* D. All articles + pagination — compact cards, denser grid */}
        <section id="all-articles" aria-labelledby="all-articles-heading" className="scroll-mt-28">
          <SectionHeading
            id="all-articles-heading"
            title="همه مقالات"
            subtitle={
              total > 0
                ? `${formatNumber(total)} مقاله — حداکثر ${formatNumber(ARTICLES_PAGE_SIZE)} در هر صفحه`
                : "فهرست کامل مجله"
            }
          />
          {showLoading ? (
            <div className="grid grid-cols-2 gap-2 sm:gap-2.5 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {Array.from({ length: 10 }).map((_, i) => (
                <ArticleCardSkeleton key={i} variant="tile" />
              ))}
            </div>
          ) : pageItems.length === 0 ? (
            <p className="rounded-2xl bg-card px-5 py-12 text-center text-sm text-[#5E5F5E]">
              مقاله‌ای برای نمایش نیست.
            </p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-2 sm:gap-2.5 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
                {pageItems.map((article, i) => (
                  <ArticleCard
                    key={article.id}
                    article={article}
                    variant="tile"
                    index={i}
                  />
                ))}
              </div>
              <PaginationNav
                page={page}
                totalPages={totalPages}
                hrefForPage={hrefForPage}
                ariaLabel="صفحه‌بندی مقالات"
              />
            </>
          )}
        </section>

        <div className="border-t border-border/50 pt-2 text-center">
          <Link
            href="/"
            className="text-sm font-bold text-[#5E5F5E] transition hover:text-[#D02327]"
          >
            بازگشت به فروشگاه
          </Link>
        </div>
      </Container>
    </div>
  );
}
