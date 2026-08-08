"use client";

import Link from "next/link";
import { SafeImage } from "@/components/ui/safe-image";
import { ProductPlaceholder } from "@/components/ui/product-placeholder";
import { CONTENT_IMAGE_QUALITY } from "@/lib/cwv";
import { toSafeNextImageSrc } from "@/lib/image-remote-patterns";
import { productPath } from "@/lib/product-url";
import { cn, formatNumber } from "@/lib/utils";
import type { ProductSummary } from "@/types/product";

const LIMIT = 12;
/** Digikala-style rail: 3 ranked rows per column, columns scroll on narrow viewports. */
const ROWS_PER_COLUMN = 3;

/**
 * Rank catalog for the «پربازدید دیروز» home rail.
 * Live API has no product view / popularity sort — do not invent counts.
 * Prefer recent `updated_at`, then availability / originality cues.
 */
export function rankYesterdayMostViewed(
  products: ProductSummary[],
  limit = LIMIT,
): ProductSummary[] {
  return [...products]
    .filter((p) => p.availability !== false)
    .sort((a, b) => {
      const ta = a.updated_at ? Date.parse(a.updated_at) : NaN;
      const tb = b.updated_at ? Date.parse(b.updated_at) : NaN;
      const aOk = Number.isFinite(ta);
      const bOk = Number.isFinite(tb);
      if (aOk && bOk && ta !== tb) return tb - ta;
      if (aOk !== bOk) return aOk ? -1 : 1;

      const score = (p: ProductSummary) =>
        (p.is_original ? 4 : 0) +
        (p.stock_status === "موجود" ||
        p.stock_status === "in_stock" ||
        p.availability
          ? 3
          : 0) +
        ((p.discount_percent ?? 0) > 0 ? 1 : 0);
      return score(b) - score(a);
    })
    .slice(0, limit);
}

function chunkColumns<T>(items: T[], size: number): T[][] {
  const columns: T[][] = [];
  for (let i = 0; i < items.length; i += size) {
    columns.push(items.slice(i, i + size));
  }
  return columns;
}

function RankBadge({ rank }: { rank: number }) {
  return (
    <span
      aria-hidden
      className={cn(
        "grid h-7 w-7 shrink-0 place-items-center rounded-full text-[12px] font-black tnum",
        "bg-[#D02327] text-white ring-1 ring-[#D02327]/30",
        "shadow-[0_6px_16px_-8px_rgba(208,35,39,0.65)]",
        "transition-[transform,box-shadow] duration-300 ease-out",
        "motion-safe:group-hover:scale-110",
        "motion-safe:group-hover:shadow-[0_10px_22px_-8px_rgba(208,35,39,0.75)]",
      )}
    >
      {formatNumber(rank)}
    </span>
  );
}

function RankedProductRow({
  product,
  rank,
  showDivider,
}: {
  product: ProductSummary;
  rank: number;
  showDivider?: boolean;
}) {
  const thumb = toSafeNextImageSrc(product.thumbnail);
  const href = productPath(product);

  return (
    <li
      value={rank}
      className={cn(
        "min-w-0",
        showDivider && "border-b border-steel/[0.09]",
      )}
    >
      <Link
        href={href}
        className={cn(
          "group flex min-h-[4.25rem] items-center gap-2.5 rounded-xl px-1.5 py-2.5 sm:gap-3 sm:px-2 sm:py-3",
          "transition-[background-color,transform] duration-300 ease-out",
          "hover:bg-[#D02327]/[0.04] motion-safe:hover:-translate-y-px",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/40",
        )}
      >
        <span
          className={cn(
            "relative grid h-14 w-14 shrink-0 place-items-center overflow-hidden rounded-xl sm:h-16 sm:w-16",
            "bg-gradient-to-br from-white to-[#F3F2F1]",
            "ring-1 ring-steel/[0.08]",
            "shadow-[0_8px_20px_-14px_rgba(94,95,94,0.45)]",
            "transition-[box-shadow,ring-color] duration-300",
            "group-hover:ring-[#D02327]/20",
            "group-hover:shadow-[0_12px_28px_-14px_rgba(208,35,39,0.28)]",
          )}
        >
          {thumb ? (
            <SafeImage
              src={thumb}
              alt=""
              width={64}
              height={64}
              quality={CONTENT_IMAGE_QUALITY}
              className="h-full w-full object-contain p-1.5 transition-transform duration-300 motion-safe:group-hover:scale-[1.04]"
              fallback={
                <ProductPlaceholder
                  name={product.name}
                  sku={product.sku}
                  className="h-full w-full"
                />
              }
            />
          ) : (
            <ProductPlaceholder
              name={product.name}
              sku={product.sku}
              className="h-full w-full"
            />
          )}
        </span>

        <RankBadge rank={rank} />

        <span className="min-w-0 flex-1 text-start">
          <span
            className={cn(
              "line-clamp-2 text-[13px] font-bold leading-snug text-foreground sm:text-sm",
              "transition-colors duration-300 group-hover:text-[#D02327]",
            )}
          >
            {product.name}
          </span>
          {product.brand?.name ? (
            <span className="mt-0.5 block truncate text-[11px] font-medium text-steel/70">
              {product.brand.name}
            </span>
          ) : null}
        </span>
      </Link>
    </li>
  );
}

function SkeletonColumn() {
  return (
    <ol
      aria-hidden
      className="flex w-[min(82vw,19.5rem)] shrink-0 flex-col lg:w-auto lg:min-w-0 lg:flex-1"
    >
      {Array.from({ length: ROWS_PER_COLUMN }).map((_, i) => (
        <li
          key={i}
          className={cn(
            "flex min-h-[4.25rem] items-center gap-2.5 px-1.5 py-2.5 sm:gap-3 sm:px-2 sm:py-3",
            i < ROWS_PER_COLUMN - 1 && "border-b border-steel/[0.09]",
          )}
        >
          <span className="h-14 w-14 shrink-0 animate-pulse rounded-xl bg-steel/[0.08] sm:h-16 sm:w-16" />
          <span className="h-7 w-7 shrink-0 animate-pulse rounded-full bg-[#D02327]/25" />
          <span className="min-w-0 flex-1 space-y-2">
            <span className="block h-3.5 w-[88%] animate-pulse rounded bg-steel/[0.08]" />
            <span className="block h-3 w-[42%] animate-pulse rounded bg-steel/[0.06]" />
          </span>
        </li>
      ))}
    </ol>
  );
}

export function MostViewedYesterdaySection({
  products,
  isLoading = false,
}: {
  products: ProductSummary[];
  isLoading?: boolean;
}) {
  if (!isLoading && products.length === 0) return null;

  const columns = isLoading
    ? null
    : chunkColumns(
        products.map((product, index) => ({ product, rank: index + 1 })),
        ROWS_PER_COLUMN,
      );

  return (
    <section
      aria-labelledby="home-most-viewed-yesterday-heading"
      className="relative overflow-hidden rounded-[1.75rem] ring-1 ring-steel/[0.08]"
    >
      {/* Soft industrial atmosphere — steel wash + brand red whisper */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background: [
            "radial-gradient(ellipse 55% 50% at 92% 8%, rgba(208,35,39,0.07) 0%, transparent 62%)",
            "radial-gradient(ellipse 45% 40% at 8% 92%, rgba(94,95,94,0.06) 0%, transparent 58%)",
            "linear-gradient(165deg, #FFFFFF 0%, #F7F6F5 48%, #F1F0EF 100%)",
          ].join(", "),
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-l from-transparent via-[#D02327]/25 to-transparent"
      />

      <div className="relative px-4 py-6 sm:px-6 sm:py-7 md:px-8 md:py-8">
        <header className="mb-5 text-center sm:mb-6">
          <p className="text-[11px] font-black tracking-normal text-[#D02327]">
            کارزار · پربازدید
          </p>
          <h2
            id="home-most-viewed-yesterday-heading"
            className="mt-2 type-section text-foreground"
          >
            پربازدیدترین کالاهای روز گذشته
          </h2>
          <p className="type-lede mx-auto mt-1.5 max-w-md text-muted-foreground">
            انتخاب‌های داغ کاتالوگ — رتبه‌بندی از موجودی زنده فروشگاه
          </p>
        </header>

        {/*
          Soft Karzar rail: .h-scroll + touch-manipulation (pan-x AND pan-y).
          Do NOT use touch-pan-x / touch-action:none — those trap vertical page scroll.
          lg: columns flex-fill the width (no sideways drag when everything fits).
        */}
        <div
          className={cn(
            "no-scrollbar h-scroll flex w-full min-w-0 gap-3 sm:gap-4 lg:gap-5",
            "overflow-x-auto overflow-y-hidden overscroll-x-contain",
            "touch-manipulation",
            "lg:overflow-x-visible lg:overscroll-x-auto",
          )}
        >
          {isLoading
            ? Array.from({ length: Math.ceil(LIMIT / ROWS_PER_COLUMN) }).map(
                (_, i) => <SkeletonColumn key={i} />,
              )
            : columns!.map((column, colIndex) => (
                <ol
                  key={colIndex}
                  className="flex w-[min(82vw,19.5rem)] shrink-0 flex-col lg:w-auto lg:min-w-0 lg:flex-1"
                >
                  {column.map(({ product, rank }, rowIndex) => (
                    <RankedProductRow
                      key={product.id}
                      product={product}
                      rank={rank}
                      showDivider={rowIndex < column.length - 1}
                    />
                  ))}
                </ol>
              ))}
        </div>
      </div>
    </section>
  );
}
