import Link from "next/link";
import { ChevronLeft, ChevronRight } from "react-iconly";
import { cn, formatNumber } from "@/lib/utils";

export type PaginationNavProps = {
  page: number;
  totalPages: number;
  /** Build href for a target page (1-based). */
  hrefForPage: (page: number) => string;
  ariaLabel: string;
  className?: string;
};

export function PaginationNav({
  page,
  totalPages,
  hrefForPage,
  ariaLabel,
  className,
}: PaginationNavProps) {
  if (totalPages <= 1) return null;

  const windowSize = 5;
  let start = Math.max(1, page - Math.floor(windowSize / 2));
  const end = Math.min(totalPages, start + windowSize - 1);
  start = Math.max(1, end - windowSize + 1);
  const pages = Array.from({ length: end - start + 1 }, (_, i) => start + i);

  const prevHref = page > 1 ? hrefForPage(page - 1) : null;
  const nextHref = page < totalPages ? hrefForPage(page + 1) : null;

  return (
    <nav
      aria-label={ariaLabel}
      className={cn("mt-8 flex flex-wrap items-center justify-center gap-2", className)}
    >
      {prevHref ? (
        <Link
          href={prevHref}
          rel="prev"
          className="inline-flex h-10 items-center gap-1 rounded-xl border border-border/60 bg-card px-3 text-xs font-bold text-[#5E5F5E] transition hover:text-[#D02327]"
        >
          <ChevronRight size="small" set="light" />
          قبلی
        </Link>
      ) : (
        <span
          className="inline-flex h-10 items-center gap-1 rounded-xl border border-border/60 bg-card px-3 text-xs font-bold text-[#5E5F5E]/40"
          aria-disabled="true"
        >
          <ChevronRight size="small" set="light" />
          قبلی
        </span>
      )}
      {start > 1 ? (
        <>
          <PageLink n={1} active={page === 1} href={hrefForPage(1)} />
          {start > 2 ? <span className="px-1 text-[#5E5F5E]/50">…</span> : null}
        </>
      ) : null}
      {pages.map((n) => (
        <PageLink key={n} n={n} active={page === n} href={hrefForPage(n)} />
      ))}
      {end < totalPages ? (
        <>
          {end < totalPages - 1 ? <span className="px-1 text-[#5E5F5E]/50">…</span> : null}
          <PageLink n={totalPages} active={page === totalPages} href={hrefForPage(totalPages)} />
        </>
      ) : null}
      {nextHref ? (
        <Link
          href={nextHref}
          rel="next"
          className="inline-flex h-10 items-center gap-1 rounded-xl border border-border/60 bg-card px-3 text-xs font-bold text-[#5E5F5E] transition hover:text-[#D02327]"
        >
          بعدی
          <ChevronLeft size="small" set="light" />
        </Link>
      ) : (
        <span
          className="inline-flex h-10 items-center gap-1 rounded-xl border border-border/60 bg-card px-3 text-xs font-bold text-[#5E5F5E]/40"
          aria-disabled="true"
        >
          بعدی
          <ChevronLeft size="small" set="light" />
        </span>
      )}
    </nav>
  );
}

function PageLink({
  n,
  active,
  href,
}: {
  n: number;
  active: boolean;
  href: string;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "grid h-10 min-w-10 place-items-center rounded-xl px-2.5 text-sm font-bold transition",
        active
          ? "bg-[#D02327] text-white shadow-[0_10px_24px_-14px_rgba(208,35,39,0.8)]"
          : "border border-border/60 bg-card text-[#5E5F5E] hover:text-[#D02327]",
      )}
    >
      {formatNumber(n)}
    </Link>
  );
}
