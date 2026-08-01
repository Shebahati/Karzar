"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Calendar, Show, TimeCircle } from "react-iconly";
import { SafeImage } from "@/components/ui/safe-image";
import { articleCategory } from "@/lib/articles";
import { cn, formatNumber } from "@/lib/utils";
import type { Article } from "@/types/content";

function faDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("fa-IR", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return "";
  }
}

function CoverFallback({ title }: { title: string }) {
  return (
    <span className="grid h-full w-full place-items-center bg-gradient-to-br from-[#5E5F5E]/15 via-[#F3F3F3] to-[#D02327]/10 text-3xl font-bold text-[#5E5F5E]/35">
      {(title || "ک").slice(0, 1)}
    </span>
  );
}

export function ArticleCard({
  article,
  variant = "default",
  priority = false,
  className,
  index = 0,
}: {
  article: Article;
  variant?: "default" | "featured" | "compact" | "rail" | "side";
  priority?: boolean;
  className?: string;
  index?: number;
}) {
  const category = articleCategory(article);
  const hasViews = typeof article.views === "number" && Number.isFinite(article.views);
  const dateLabel = article.published_at ? faDate(article.published_at) : "";
  const href = `/blog/${article.slug}`;

  const meta = (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[10px] text-[#5E5F5E]",
        variant === "featured" && "text-[11px]",
        variant === "side" && "text-[10px]",
      )}
    >
      {dateLabel ? (
        <span className="inline-flex items-center gap-1">
          <Calendar size="small" set="light" />
          {dateLabel}
        </span>
      ) : null}
      {typeof article.reading_minutes === "number" ? (
        <span className="inline-flex items-center gap-1">
          <TimeCircle size="small" set="light" />
          {formatNumber(article.reading_minutes)} دقیقه
        </span>
      ) : null}
      {hasViews ? (
        <span className="inline-flex items-center gap-1">
          <Show size="small" set="light" />
          {formatNumber(article.views)} بازدید
        </span>
      ) : null}
    </div>
  );

  const body = (
    <>
      {category ? (
        <span
          className={cn(
            "inline-flex w-fit rounded-md bg-[#D02327]/[0.08] px-1.5 py-0.5 text-[10px] font-bold text-[#D02327]",
            variant === "featured" && "text-[11px]",
          )}
        >
          {category}
        </span>
      ) : null}
      <h3
        className={cn(
          "font-bold leading-snug text-foreground transition-colors group-hover:text-[#D02327]",
          variant === "featured" && "text-lg sm:text-xl lg:text-[1.35rem] lg:leading-8",
          variant === "default" && "line-clamp-2 text-[0.95rem] leading-6",
          variant === "compact" && "line-clamp-2 text-sm leading-5",
          variant === "rail" && "line-clamp-2 text-sm leading-5",
          variant === "side" && "line-clamp-2 text-sm leading-5",
        )}
      >
        {article.title}
      </h3>
      {article.excerpt && variant !== "compact" && variant !== "side" ? (
        <p
          className={cn(
            "text-sm leading-6 text-[#5E5F5E]",
            variant === "featured" ? "line-clamp-2 text-[13px] leading-5" : "line-clamp-2",
            variant === "rail" && "line-clamp-2 text-xs leading-5",
          )}
        >
          {article.excerpt}
        </p>
      ) : null}
      {meta}
    </>
  );

  if (variant === "featured") {
    return (
      <motion.article
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-40px" }}
        transition={{ duration: 0.45, delay: 0.04 }}
        className={cn("h-full", className)}
      >
        <Link
          href={href}
          className="group relative flex h-full min-h-[200px] flex-col overflow-hidden rounded-[1.15rem] bg-card sm:min-h-[220px] lg:min-h-[248px]"
        >
          <div className="absolute inset-0">
            {article.cover_image ? (
              <SafeImage
                src={article.cover_image}
                alt={article.title}
                fill
                priority={priority}
                sizes="(max-width: 1024px) 100vw, 55vw"
                className="object-cover transition-transform duration-700 ease-out group-hover:scale-[1.03]"
                fallback={<CoverFallback title={article.title} />}
              />
            ) : (
              <CoverFallback title={article.title} />
            )}
            <div
              aria-hidden
              className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-black/5"
            />
            <div
              aria-hidden
              className="absolute inset-0 opacity-35"
              style={{
                backgroundImage:
                  "radial-gradient(circle at 20% 20%, rgba(208,35,39,0.22), transparent 45%), radial-gradient(circle at 85% 70%, rgba(94,95,94,0.18), transparent 40%)",
              }}
            />
          </div>
          <div className="relative mt-auto flex flex-col gap-1.5 p-4 text-white sm:gap-2 sm:p-5">
            {category ? (
              <span className="inline-flex w-fit rounded-md bg-white/15 px-2 py-0.5 text-[11px] font-bold backdrop-blur-sm">
                {category}
              </span>
            ) : null}
            <h3 className="text-lg font-bold leading-7 sm:text-xl sm:leading-8 lg:text-[1.35rem] lg:leading-8">
              {article.title}
            </h3>
            {article.excerpt ? (
              <p className="line-clamp-2 max-w-xl text-[13px] leading-5 text-white/80">
                {article.excerpt}
              </p>
            ) : null}
            <div className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[11px] text-white/75">
              {dateLabel ? (
                <span className="inline-flex items-center gap-1">
                  <Calendar size="small" set="light" />
                  {dateLabel}
                </span>
              ) : null}
              {typeof article.reading_minutes === "number" ? (
                <span className="inline-flex items-center gap-1">
                  <TimeCircle size="small" set="light" />
                  {formatNumber(article.reading_minutes)} دقیقه
                </span>
              ) : null}
              {hasViews ? (
                <span className="inline-flex items-center gap-1">
                  <Show size="small" set="light" />
                  {formatNumber(article.views)} بازدید
                </span>
              ) : null}
            </div>
          </div>
        </Link>
      </motion.article>
    );
  }

  if (variant === "side") {
    return (
      <motion.article
        initial={{ opacity: 0, y: 14 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-40px" }}
        transition={{ duration: 0.4, delay: (index % 4) * 0.05 }}
        className={cn("h-full", className)}
      >
        <Link
          href={href}
          className={cn(
            "group flex h-full overflow-hidden rounded-[1.05rem] bg-card",
            "shadow-[0_8px_22px_-20px_rgba(94,95,94,0.5)]",
            "transition-[transform,box-shadow] duration-300 ease-out",
            "hover:-translate-y-0.5 hover:shadow-[0_14px_32px_-22px_rgba(208,35,39,0.26)]",
          )}
        >
          <div className="relative w-[108px] shrink-0 overflow-hidden bg-[#EDEDED] sm:w-[120px]">
            {article.cover_image ? (
              <SafeImage
                src={article.cover_image}
                alt={article.title}
                fill
                priority={priority}
                sizes="120px"
                className="object-cover transition-transform duration-500 ease-out group-hover:scale-105"
                fallback={<CoverFallback title={article.title} />}
              />
            ) : (
              <CoverFallback title={article.title} />
            )}
          </div>
          <div className="flex min-w-0 flex-1 flex-col justify-center gap-1.5 p-3 sm:p-3.5">
            {body}
          </div>
        </Link>
      </motion.article>
    );
  }

  const mediaAspect =
    variant === "rail"
      ? "aspect-[16/10]"
      : variant === "compact"
        ? "aspect-[16/9]"
        : "aspect-[16/9]";

  return (
    <motion.article
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.4, delay: (index % 4) * 0.05 }}
      className={cn("h-full", className)}
    >
      <Link
        href={href}
        className={cn(
          "group flex h-full flex-col overflow-hidden rounded-[1.1rem] bg-card",
          "shadow-[0_8px_22px_-20px_rgba(94,95,94,0.5)]",
          "transition-[transform,box-shadow] duration-300 ease-out",
          "hover:-translate-y-0.5 hover:shadow-[0_14px_32px_-22px_rgba(208,35,39,0.26)]",
          variant === "rail" && "rounded-2xl",
        )}
      >
        <div className={cn("relative overflow-hidden bg-[#EDEDED]", mediaAspect)}>
          {article.cover_image ? (
            <SafeImage
              src={article.cover_image}
              alt={article.title}
              fill
              priority={priority}
              sizes={
                variant === "rail"
                  ? "240px"
                  : "(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
              }
              className="object-cover transition-transform duration-500 ease-out group-hover:scale-105"
              fallback={<CoverFallback title={article.title} />}
            />
          ) : (
            <CoverFallback title={article.title} />
          )}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/10 via-transparent to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          />
        </div>
        <div
          className={cn(
            "flex flex-1 flex-col gap-1.5 p-3.5",
            variant === "default" && "gap-2 p-4",
            variant === "rail" && "p-3",
            variant === "compact" && "gap-1.5 p-3",
          )}
        >
          {body}
        </div>
      </Link>
    </motion.article>
  );
}

export function ArticleCardSkeleton({
  variant = "default",
  className,
}: {
  variant?: "default" | "featured" | "rail" | "side";
  className?: string;
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-[1.1rem] bg-card",
        variant === "featured" &&
          "min-h-[200px] rounded-[1.15rem] sm:min-h-[220px] lg:min-h-[248px]",
        variant === "side" && "flex h-[104px] sm:h-[112px]",
        className,
      )}
    >
      {variant === "side" ? (
        <>
          <div className="w-[108px] shrink-0 animate-pulse bg-[#E8E8E8] sm:w-[120px]" />
          <div className="flex flex-1 flex-col justify-center gap-2 p-3.5">
            <div className="h-2.5 w-14 animate-pulse rounded bg-[#E8E8E8]" />
            <div className="h-3.5 w-4/5 animate-pulse rounded bg-[#E8E8E8]" />
            <div className="h-2.5 w-1/2 animate-pulse rounded bg-[#E8E8E8]" />
          </div>
        </>
      ) : (
        <>
          <div
            className={cn(
              "animate-pulse bg-[#E8E8E8]",
              variant === "featured" ? "h-full min-h-[inherit]" : "aspect-[16/9]",
            )}
          />
          {variant !== "featured" ? (
            <div className="space-y-2 p-4">
              <div className="h-2.5 w-14 animate-pulse rounded bg-[#E8E8E8]" />
              <div className="h-3.5 w-4/5 animate-pulse rounded bg-[#E8E8E8]" />
              <div className="h-2.5 w-full animate-pulse rounded bg-[#E8E8E8]" />
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
