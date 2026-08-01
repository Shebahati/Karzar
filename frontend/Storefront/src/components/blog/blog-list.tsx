"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "react-iconly";
import { ArticleCard, ArticleCardSkeleton } from "@/components/blog/article-card";
import { SectionHeading } from "@/components/home/section-heading";
import { AutoCarousel } from "@/components/ui/auto-carousel";
import { Container } from "@/components/ui/container";
import { useArticles } from "@/features/catalog/queries";
import {
  ARTICLES_PAGE_SIZE,
  groupArticlesByCategory,
  paginateArticles,
  sortArticlesByNewest,
  sortArticlesByViews,
} from "@/lib/articles";
import { cn, formatNumber } from "@/lib/utils";
import type { Article } from "@/types/content";

function ArticlesPagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;

  const windowSize = 5;
  let start = Math.max(1, page - Math.floor(windowSize / 2));
  const end = Math.min(totalPages, start + windowSize - 1);
  start = Math.max(1, end - windowSize + 1);
  const pages = Array.from({ length: end - start + 1 }, (_, i) => start + i);

  return (
    <nav
      aria-label="صفحه‌بندی مقالات"
      className="mt-8 flex flex-wrap items-center justify-center gap-2"
    >
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        className="inline-flex h-10 items-center gap-1 rounded-xl border border-border/60 bg-card px-3 text-xs font-bold text-[#5E5F5E] transition hover:text-[#D02327] disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronRight size="small" set="light" />
        قبلی
      </button>
      {start > 1 ? (
        <>
          <PageBtn n={1} active={page === 1} onClick={onPageChange} />
          {start > 2 ? <span className="px-1 text-[#5E5F5E]/50">…</span> : null}
        </>
      ) : null}
      {pages.map((n) => (
        <PageBtn key={n} n={n} active={n === page} onClick={onPageChange} />
      ))}
      {end < totalPages ? (
        <>
          {end < totalPages - 1 ? <span className="px-1 text-[#5E5F5E]/50">…</span> : null}
          <PageBtn n={totalPages} active={page === totalPages} onClick={onPageChange} />
        </>
      ) : null}
      <button
        type="button"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        className="inline-flex h-10 items-center gap-1 rounded-xl border border-border/60 bg-card px-3 text-xs font-bold text-[#5E5F5E] transition hover:text-[#D02327] disabled:pointer-events-none disabled:opacity-40"
      >
        بعدی
        <ChevronLeft size="small" set="light" />
      </button>
    </nav>
  );
}

function PageBtn({
  n,
  active,
  onClick,
}: {
  n: number;
  active: boolean;
  onClick: (page: number) => void;
}) {
  return (
    <button
      type="button"
      aria-current={active ? "page" : undefined}
      onClick={() => onClick(n)}
      className={cn(
        "grid h-10 min-w-10 place-items-center rounded-xl px-2.5 text-sm font-bold transition",
        active
          ? "bg-[#D02327] text-white shadow-[0_10px_24px_-14px_rgba(208,35,39,0.8)]"
          : "border border-border/60 bg-card text-[#5E5F5E] hover:text-[#D02327]",
      )}
    >
      {formatNumber(n)}
    </button>
  );
}

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
    <section aria-labelledby="magazine-topics-heading" className="space-y-6">
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
        className="relative flex gap-1 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
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
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {articles.map((article, i) => (
                  <ArticleCard
                    key={`${active.label}-${article.id}`}
                    article={article}
                    variant="compact"
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

export function BlogList() {
  const { data, isLoading } = useArticles();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const pageFromUrl = Math.max(1, Number(searchParams.get("page") || "1") || 1);

  const newest = useMemo(
    () => sortArticlesByNewest(data ?? []),
    [data],
  );

  const mostViewedSorted = useMemo(
    () => sortArticlesByViews(data ?? []),
    [data],
  );

  const mostViewed = useMemo(() => {
    if (mostViewedSorted) return mostViewedSorted.slice(0, 8);
    // No views in API — complementary strip after the asymmetric newest block.
    return newest.slice(3, 11);
  }, [mostViewedSorted, newest]);

  const categoryGroups = useMemo(
    () => groupArticlesByCategory(data ?? [], { minPerGroup: 1, maxGroups: 6 }),
    [data],
  );

  const allSorted = newest;
  const { items: pageItems, page, totalPages, total } = paginateArticles(
    allSorted,
    pageFromUrl,
    ARTICLES_PAGE_SIZE,
  );

  const setPage = (next: number) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next <= 1) params.delete("page");
    else params.set("page", String(next));
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    const el = document.getElementById("all-articles");
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

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

      <Container className="space-y-12 py-9 lg:space-y-14 lg:py-12">
        <header className="mx-auto max-w-2xl text-center">
          <span className="inline-block rounded-full bg-[#D02327]/[0.08] px-3 py-1 text-xs font-bold text-[#D02327]">
            مجله کارزار
          </span>
          <h1 className="mt-3 text-3xl font-bold text-foreground sm:text-4xl">
            دانش، راهنما و دنیای ابزار
          </h1>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[#5E5F5E]">
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
          {isLoading ? (
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
              {restNewest.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {restNewest.map((article, i) => (
                    <ArticleCard
                      key={article.id}
                      article={article}
                      variant="compact"
                      index={i + 2}
                    />
                  ))}
                </div>
              ) : null}
            </div>
          )}
        </section>

        {/* B. Most viewed */}
        {!isLoading && mostViewed.length > 0 ? (
          <section aria-labelledby="most-viewed-heading">
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
        {!isLoading && categoryGroups.length > 0 ? (
          <MagazineCategoryTabs groups={categoryGroups} />
        ) : null}

        {/* D. All articles + pagination */}
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
          {isLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <ArticleCardSkeleton key={i} />
              ))}
            </div>
          ) : pageItems.length === 0 ? (
            <p className="rounded-2xl bg-card px-5 py-12 text-center text-sm text-[#5E5F5E]">
              مقاله‌ای برای نمایش نیست.
            </p>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {pageItems.map((article, i) => (
                  <ArticleCard key={article.id} article={article} index={i} />
                ))}
              </div>
              <ArticlesPagination
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
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
