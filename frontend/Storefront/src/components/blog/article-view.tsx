"use client";

import { useCallback, useEffect, useState, type MouseEvent } from "react";
import Link from "next/link";
import {
  Calendar,
  ChevronDown,
  ChevronLeft,
  Show,
  TimeCircle,
  User,
} from "react-iconly";
import { Container } from "@/components/ui/container";
import { Skeleton } from "@/components/ui/skeleton";
import { SafeImage } from "@/components/ui/safe-image";
import { SectionHeading } from "@/components/home/section-heading";
import { ProductCarousel } from "@/components/home/product-carousel";
import { useArticle, useProductsByIds } from "@/features/catalog/queries";
import { articleCategory } from "@/lib/articles";
import {
  prepareArticleContent,
  type ArticleTocItem,
} from "@/lib/article-toc";
import { cn, formatNumber } from "@/lib/utils";
import { extractArticleSeo, type BlogBlock, type BlogFaqItem } from "@/types/content";
import { toSafeNextImageSrc } from "@/lib/image-remote-patterns";

function faDate(iso: string) {
  return new Date(iso).toLocaleDateString("fa-IR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function scrollToSection(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "start" });
  try {
    history.replaceState(null, "", `#${id}`);
  } catch {
    /* ignore */
  }
}

export function ArticleView({ slug }: { slug: string }) {
  const { data: post, isLoading, isError } = useArticle(slug);
  const related = useProductsByIds(post?.related_product_ids ?? []);

  if (isLoading) {
    return (
      <Container className="py-10">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="mt-6 h-10 w-3/4" />
        <Skeleton className="mt-4 h-4 w-56" />
        <Skeleton className="mt-8 aspect-[16/8] w-full rounded-2xl" />
        <div className="mx-auto mt-8 max-w-prose space-y-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-4/6" />
        </div>
      </Container>
    );
  }

  if (isError || !post) {
    return (
      <Container className="py-20 text-center">
        <p className="text-lg font-bold text-foreground">مقاله یافت نشد</p>
        <Link href="/blog" className="mt-4 inline-block text-sm font-bold text-[#D02327]">
          بازگشت به مجله
        </Link>
      </Container>
    );
  }

  const { bodyBlocks } = extractArticleSeo(post);
  const { toc, bodyBlocks: sections, headingIds } = prepareArticleContent(bodyBlocks);
  const category = articleCategory(post);
  const hasViews = typeof post.views === "number" && Number.isFinite(post.views);
  const lead = post.excerpt?.trim() || null;

  return (
    <article
      itemScope
      itemType="https://schema.org/Article"
      className="relative overflow-x-clip"
    >
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(60%_70%_at_100%_0%,rgba(208,35,39,0.07),transparent_70%),radial-gradient(45%_50%_at_0%_20%,rgba(94,95,94,0.06),transparent_65%)]"
        aria-hidden
      />

      <Container className="relative py-8 lg:py-12">
        <nav
          aria-label="breadcrumb"
          className="mb-6 flex items-center gap-1.5 text-xs text-[#5E5F5E]"
        >
          <Link href="/" className="transition hover:text-[#D02327]">
            خانه
          </Link>
          <ChevronLeft size="small" set="light" />
          <Link href="/blog" className="transition hover:text-[#D02327]">
            مجله کارزار
          </Link>
          <ChevronLeft size="small" set="light" />
          <span className="line-clamp-1 text-foreground">{post.title}</span>
        </nav>

        <header className="mx-auto max-w-3xl text-center">
          {category ? (
            <span className="inline-flex rounded-md bg-[#D02327]/[0.08] px-2.5 py-1 text-[11px] font-bold text-[#D02327]">
              {category}
            </span>
          ) : post.tags?.length ? (
            <div className="flex flex-wrap justify-center gap-2">
              {post.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="rounded-md bg-[#D02327]/[0.08] px-2.5 py-1 text-[11px] font-bold text-[#D02327]"
                >
                  {tag}
                </span>
              ))}
            </div>
          ) : null}

          <h1
            itemProp="headline"
            className="mt-4 text-[1.65rem] font-bold leading-snug text-foreground sm:text-3xl lg:text-4xl lg:leading-tight"
          >
            {post.title}
          </h1>

          <div className="mt-5 flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-[12px] text-[#5E5F5E] sm:text-sm">
            {post.author ? (
              <span className="flex items-center gap-1.5" itemProp="author">
                <User size="small" set="light" />
                {post.author}
              </span>
            ) : null}
            <time
              className="flex items-center gap-1.5"
              dateTime={post.published_at}
              itemProp="datePublished"
            >
              <Calendar size="small" set="light" />
              {faDate(post.published_at)}
            </time>
            <span className="flex items-center gap-1.5">
              <TimeCircle size="small" set="light" />
              {formatNumber(post.reading_minutes)} دقیقه مطالعه
            </span>
            {hasViews ? (
              <span className="flex items-center gap-1.5">
                <Show size="small" set="light" />
                {formatNumber(post.views)} بازدید
              </span>
            ) : null}
          </div>
        </header>

        {toSafeNextImageSrc(post.cover_image) ? (
          <div className="relative mx-auto mt-8 aspect-[16/8] max-w-4xl overflow-hidden rounded-2xl border border-[#5E5F5E]/10 shadow-[0_20px_50px_-28px_rgba(94,95,94,0.45)] sm:rounded-3xl">
            <SafeImage
              src={post.cover_image!}
              alt={post.title}
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 60vw"
              className="object-cover"
              itemProp="image"
              fallback={null}
            />
          </div>
        ) : null}

        <div
          className={cn(
            "mx-auto mt-10 grid max-w-5xl gap-8",
            toc.length > 0 && "lg:grid-cols-[minmax(0,1fr)_15.5rem] lg:items-start",
          )}
        >
          <div className={cn(toc.length > 0 && "lg:order-1")}>
            {lead ? (
              <p
                className="border-s-[3px] border-[#D02327] bg-gradient-to-l from-[#D02327]/[0.04] to-transparent py-3 pe-1 ps-4 text-[15px] font-medium leading-8 text-[#5E5F5E] sm:text-base sm:leading-9"
                itemProp="description"
              >
                {lead}
              </p>
            ) : null}

            {toc.length > 0 ? (
              <div className="mt-6 lg:hidden">
                <ArticleToc nav={toc} />
              </div>
            ) : null}

            <div
              className="prose-blog mt-8 max-w-prose space-y-5 text-[15px] leading-9 text-foreground/90"
              itemProp="articleBody"
            >
              {sections.map((block, i) => (
                <BlockRenderer key={i} block={block} headingId={headingIds.get(i)} />
              ))}
            </div>
          </div>

          {toc.length > 0 ? (
            <aside className="hidden lg:order-2 lg:block">
              <div className="sticky top-28">
                <ArticleToc nav={toc} sticky />
              </div>
            </aside>
          ) : null}
        </div>
      </Container>

      {related.data && related.data.length > 0 ? (
        <Container className="pb-16">
          <SectionHeading title="محصولات مرتبط با این مقاله" />
          <ProductCarousel products={related.data} isLoading={related.isLoading} />
        </Container>
      ) : null}
    </article>
  );
}

function ArticleToc({
  nav,
  sticky = false,
}: {
  nav: ArticleTocItem[];
  sticky?: boolean;
}) {
  const [activeId, setActiveId] = useState<string | null>(nav[0]?.id ?? null);

  useEffect(() => {
    const nodes = nav
      .map((item) => document.getElementById(item.id))
      .filter((el): el is HTMLElement => Boolean(el));
    if (!nodes.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]?.target?.id) {
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin: "-20% 0px -55% 0px", threshold: [0.1, 0.35, 0.6] },
    );

    nodes.forEach((n) => observer.observe(n));
    return () => observer.disconnect();
  }, [nav]);

  const onClick = useCallback((e: MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    scrollToSection(id);
    setActiveId(id);
  }, []);

  return (
    <nav
      aria-label="منوی مطالب"
      className={cn(
        "overflow-hidden rounded-2xl border border-[#5E5F5E]/12 bg-card/90",
        sticky && "shadow-[0_16px_40px_-28px_rgba(94,95,94,0.55)]",
      )}
    >
      <div className="flex items-center gap-2 border-b border-[#5E5F5E]/10 bg-gradient-to-l from-[#D02327]/[0.06] to-transparent px-4 py-3">
        <span className="h-4 w-1 shrink-0 rounded-full bg-[#D02327]" aria-hidden />
        <p className="text-sm font-bold text-foreground">منو</p>
        <span className="ms-auto text-[10px] font-bold text-[#5E5F5E]/70">
          {formatNumber(nav.length)} بخش
        </span>
      </div>
      <ol className="max-h-[min(70vh,28rem)] space-y-0.5 overflow-y-auto p-2.5">
        {nav.map((item, index) => {
          const active = activeId === item.id;
          return (
            <li key={item.id}>
              <a
                href={`#${item.id}`}
                onClick={(e) => onClick(e, item.id)}
                className={cn(
                  "flex gap-2 rounded-xl px-2.5 py-2 text-[13px] leading-6 transition",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/35",
                  item.level === 3 && "ps-5 text-[12.5px]",
                  active
                    ? "bg-[#D02327]/[0.08] font-bold text-[#D02327]"
                    : "text-[#5E5F5E] hover:bg-[#5E5F5E]/[0.05] hover:text-foreground",
                )}
              >
                <span
                  className={cn(
                    "mt-0.5 shrink-0 tnum text-[11px] font-bold",
                    active ? "text-[#D02327]" : "text-[#5E5F5E]/45",
                  )}
                >
                  {formatNumber(index + 1)}
                </span>
                <span>{item.text}</span>
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function BlockRenderer({
  block,
  headingId,
}: {
  block: BlogBlock;
  headingId?: string;
}) {
  switch (block.type) {
    case "meta":
      return null;
    case "heading":
      return (
        <h2
          id={headingId}
          className="scroll-mt-28 border-b border-[#5E5F5E]/10 pb-2 pt-5 text-xl font-bold text-foreground"
        >
          {block.text}
        </h2>
      );
    case "subheading":
      return (
        <h3
          id={headingId}
          className="scroll-mt-28 pt-3 text-lg font-bold text-foreground"
        >
          {block.text}
        </h3>
      );
    case "list":
      if (block.ordered) {
        return (
          <ol className="list-decimal space-y-2 pe-5">
            {block.items.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ol>
        );
      }
      return (
        <ul className="space-y-2">
          {block.items.map((item, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-3 h-1.5 w-1.5 shrink-0 rounded-full bg-[#D02327]" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      );
    case "table":
      return (
        <figure className="my-6 h-scroll max-w-full rounded-2xl border border-[#5E5F5E]/12">
          {block.caption ? (
            <figcaption className="border-b border-[#5E5F5E]/10 bg-[#5E5F5E]/[0.04] px-4 py-2 text-sm font-bold text-foreground">
              {block.caption}
            </figcaption>
          ) : null}
          <table className="w-full min-w-[28rem] border-collapse text-sm">
            <thead>
              <tr className="bg-[#5E5F5E]/[0.06]">
                {block.headers.map((h) => (
                  <th
                    key={h}
                    className="border-b border-[#5E5F5E]/10 px-3 py-2.5 text-start font-bold text-foreground"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, ri) => (
                <tr key={ri} className="odd:bg-background even:bg-[#5E5F5E]/[0.03]">
                  {row.map((cell, ci) => (
                    <td key={ci} className="border-b border-[#5E5F5E]/10 px-3 py-2.5 align-top">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </figure>
      );
    case "image":
      return (
        <figure className="my-6 overflow-hidden rounded-2xl border border-[#5E5F5E]/12 bg-[#5E5F5E]/[0.03]">
          <div className="relative aspect-[16/10] w-full">
            <SafeImage
              src={block.src}
              alt={block.alt}
              fill
              sizes="(max-width: 768px) 100vw, 680px"
              className="object-cover"
              fallback={
                <span className="grid h-full w-full place-items-center text-sm text-[#5E5F5E]">
                  {block.alt || "تصویر"}
                </span>
              }
            />
          </div>
          {block.caption ? (
            <figcaption className="px-4 py-3 text-sm text-[#5E5F5E]">{block.caption}</figcaption>
          ) : null}
        </figure>
      );
    case "callout": {
      const styles =
        block.variant === "warning"
          ? "border-amber-300 bg-amber-50 text-amber-950"
          : block.variant === "tip"
            ? "border-emerald-300 bg-emerald-50 text-emerald-950"
            : "border-[#D02327]/25 bg-[#D02327]/[0.04] text-foreground";
      return (
        <aside className={`rounded-2xl border px-4 py-3 text-[14.5px] leading-8 ${styles}`}>
          {block.text}
        </aside>
      );
    }
    case "links":
      return (
        <nav
          aria-label={block.title || "لینک‌های مرتبط"}
          className="rounded-2xl border border-[#5E5F5E]/12 bg-[#5E5F5E]/[0.03] px-4 py-4"
        >
          {block.title ? (
            <p className="mb-3 text-sm font-bold text-foreground">{block.title}</p>
          ) : null}
          <ul className="space-y-2">
            {block.items.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="inline-flex items-center gap-1.5 text-[14.5px] font-bold text-[#D02327] hover:underline"
                >
                  {item.label}
                  <ChevronLeft size="small" set="light" />
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      );
    case "faq":
      return <FaqSection items={block.items} />;
    case "paragraph":
    default:
      return <p>{(block as { text?: string }).text}</p>;
  }
}

function FaqSection({ items }: { items: BlogFaqItem[] }) {
  return (
    <div className="space-y-3 pt-2">
      {items.map((item) => (
        <details
          key={item.question}
          className="group rounded-2xl border border-[#5E5F5E]/12 bg-[#5E5F5E]/[0.03] px-4 py-3 open:bg-[#5E5F5E]/[0.06]"
        >
          <summary className="cursor-pointer list-none text-[15px] font-bold text-foreground marker:content-none">
            <span className="flex items-start justify-between gap-3">
              {item.question}
              <span
                className="mt-0.5 shrink-0 text-[#5E5F5E] transition-transform duration-300 ease-out group-open:rotate-180"
                aria-hidden
              >
                <ChevronDown size="small" set="light" primaryColor="#5E5F5E" />
              </span>
            </span>
          </summary>
          <p className="mt-3 text-[14.5px] leading-8 text-foreground/85">{item.answer}</p>
        </details>
      ))}
    </div>
  );
}
