"use client";

import Image from "next/image";
import Link from "next/link";
import { Calendar, ChevronLeft, TimeCircle, User } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Skeleton } from "@/components/ui/skeleton";
import { SectionHeading } from "@/components/home/section-heading";
import { ProductCarousel } from "@/components/home/product-carousel";
import { useArticle, useProductsByIds } from "@/features/catalog/queries";
import { formatNumber } from "@/lib/utils";
import { extractArticleSeo, type BlogBlock, type BlogFaqItem } from "@/types/content";

function faDate(iso: string) {
  return new Date(iso).toLocaleDateString("fa-IR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function slugifyHeading(text: string) {
  return text
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^\u0600-\u06FFa-zA-Z0-9\-]/g, "")
    .slice(0, 80);
}

export function ArticleView({ slug }: { slug: string }) {
  const { data: post, isLoading, isError } = useArticle(slug);
  const related = useProductsByIds(post?.related_product_ids ?? []);

  if (isLoading) {
    return (
      <Container className="py-10">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="mt-6 aspect-[16/8] w-full rounded-2xl" />
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
        <Link href="/blog" className="mt-4 inline-block text-sm font-bold text-primary">
          بازگشت به مجله
        </Link>
      </Container>
    );
  }

  const { bodyBlocks } = extractArticleSeo(post);

  return (
    <article itemScope itemType="https://schema.org/Article">
      <Container className="py-8 lg:py-12">
        <nav aria-label="breadcrumb" className="mb-6 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Link href="/" className="hover:text-primary">
            خانه
          </Link>
          <ChevronLeft size="small" set="light" />
          <Link href="/blog" className="hover:text-primary">
            مجله کارزار
          </Link>
          <ChevronLeft size="small" set="light" />
          <span className="line-clamp-1 text-foreground">{post.title}</span>
        </nav>

        <header className="mx-auto max-w-3xl text-center">
          <div className="flex flex-wrap justify-center gap-2">
            {post.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-accent px-3 py-1 text-xs font-bold text-primary"
              >
                {tag}
              </span>
            ))}
          </div>
          <h1 itemProp="headline" className="mt-5 text-3xl font-bold leading-tight text-foreground sm:text-4xl">
            {post.title}
          </h1>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5" itemProp="author">
              <User size="small" set="light" />
              {post.author}
            </span>
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
          </div>
        </header>

        {post.cover_image ? (
          <div className="relative mx-auto mt-8 aspect-[16/8] max-w-4xl overflow-hidden rounded-3xl shadow-card">
            <Image
              src={post.cover_image}
              alt={post.title}
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 60vw"
              className="object-cover"
              itemProp="image"
            />
          </div>
        ) : null}

        <div
          className="prose-blog mx-auto mt-10 max-w-prose space-y-5 text-[15px] leading-9 text-foreground/90"
          itemProp="articleBody"
        >
          {bodyBlocks.map((block, i) => (
            <BlockRenderer key={i} block={block} />
          ))}
        </div>
      </Container>

      {related.data && related.data.length > 0 && (
        <Container className="pb-16">
          <SectionHeading title="محصولات مرتبط با این مقاله" />
          <ProductCarousel products={related.data} isLoading={related.isLoading} />
        </Container>
      )}
    </article>
  );
}

function BlockRenderer({ block }: { block: BlogBlock }) {
  switch (block.type) {
    case "meta":
      return null;
    case "heading":
      return (
        <h2
          id={slugifyHeading(block.text)}
          className="scroll-mt-28 pt-4 text-xl font-bold text-foreground"
        >
          {block.text}
        </h2>
      );
    case "subheading":
      return (
        <h3
          id={slugifyHeading(block.text)}
          className="scroll-mt-28 pt-2 text-lg font-bold text-foreground"
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
              <span className="mt-3 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      );
    case "table":
      return (
        <figure className="my-6 overflow-x-auto rounded-2xl border border-border">
          {block.caption ? (
            <figcaption className="border-b border-border bg-muted/40 px-4 py-2 text-sm font-bold text-foreground">
              {block.caption}
            </figcaption>
          ) : null}
          <table className="w-full min-w-[28rem] border-collapse text-sm">
            <thead>
              <tr className="bg-muted/60">
                {block.headers.map((h) => (
                  <th
                    key={h}
                    className="border-b border-border px-3 py-2.5 text-start font-bold text-foreground"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, ri) => (
                <tr key={ri} className="odd:bg-background even:bg-muted/20">
                  {row.map((cell, ci) => (
                    <td key={ci} className="border-b border-border/70 px-3 py-2.5 align-top">
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
        <figure className="my-6 overflow-hidden rounded-2xl border border-border bg-muted/20">
          <div className="relative aspect-[16/10] w-full">
            <Image
              src={block.src}
              alt={block.alt}
              fill
              sizes="(max-width: 768px) 100vw, 680px"
              className="object-cover"
            />
          </div>
          {block.caption ? (
            <figcaption className="px-4 py-3 text-sm text-muted-foreground">{block.caption}</figcaption>
          ) : null}
        </figure>
      );
    case "callout": {
      const styles =
        block.variant === "warning"
          ? "border-amber-300 bg-amber-50 text-amber-950"
          : block.variant === "tip"
            ? "border-emerald-300 bg-emerald-50 text-emerald-950"
            : "border-primary/30 bg-accent text-foreground";
      return (
        <aside className={`rounded-2xl border px-4 py-3 text-[14.5px] leading-8 ${styles}`}>
          {block.text}
        </aside>
      );
    }
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
          className="group rounded-2xl border border-border bg-muted/20 px-4 py-3 open:bg-muted/40"
        >
          <summary className="cursor-pointer list-none text-[15px] font-bold text-foreground marker:content-none">
            <span className="flex items-start justify-between gap-3">
              {item.question}
              <span className="mt-0.5 text-muted-foreground transition group-open:rotate-45">+</span>
            </span>
          </summary>
          <p className="mt-3 text-[14.5px] leading-8 text-foreground/85">{item.answer}</p>
        </details>
      ))}
    </div>
  );
}
