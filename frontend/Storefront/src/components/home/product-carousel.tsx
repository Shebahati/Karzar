"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { ChevronLeft } from "react-iconly";
import { ProductCard, ProductCardSkeleton } from "@/components/product/product-card";
import { AutoCarousel } from "@/components/ui/auto-carousel";
import { isPlpLcpIndex } from "@/lib/cwv";
import { cn } from "@/lib/utils";
import type { ProductSummary } from "@/types/product";

export type DealLeadPromo = {
  title: string;
  href: string;
  iconSrc: string;
  hrefLabel?: string;
  /** Optional short line under the CTA — never a fake countdown. */
  lede?: string;
};

/** Desktop (≥ md): Karzar steel strip behind پرتخفیف‌ها lead + deal cards. */
const DEAL_STRIP_DESKTOP =
  "md:mx-0 md:rounded-[2rem] md:border md:border-white/10 md:bg-[#5E5F5E] md:p-4 md:shadow-[0_16px_40px_-28px_rgba(0,0,0,0.35)]";

/** Mobile (< md): full-bleed brand-red strip (breaks Container px-5 / sm:px-6). */
const DEAL_STRIP_MOBILE =
  "-mx-5 overflow-hidden bg-[#D02327] py-4 sm:-mx-6 md:overflow-hidden";

/**
 * Mobile-only header: icon beside title + existing «همه» CTA.
 * Hidden from md up — desktop keeps DealPromoLead.
 */
function DealMobileHeader({
  title,
  href,
  iconSrc,
  hrefLabel = "همه",
  headingId,
}: DealLeadPromo & { headingId?: string }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3 px-5 sm:px-6 md:hidden">
      <div className="flex min-w-0 items-center gap-2.5">
        <span
          className="grid h-[50px] w-[50px] shrink-0 place-items-center rounded-full bg-white/15 ring-1 ring-white/25"
          aria-hidden
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- static public icon URL */}
          <img
            src={iconSrc}
            alt=""
            width={39}
            height={39}
            className="h-[34px] w-[34px] object-contain drop-shadow-sm"
          />
        </span>
        <h2
          id={headingId}
          className="truncate text-[1.05rem] font-bold leading-snug tracking-tight text-white"
        >
          {title}
        </h2>
      </div>

      <Link
        href={href}
        className="inline-flex shrink-0 items-center gap-0.5 text-[13px] font-bold text-white/95 transition-opacity hover:opacity-90"
      >
        {hrefLabel}
        <ChevronLeft size="small" set="light" primaryColor="currentColor" />
      </Link>
    </div>
  );
}

/** Desktop lead promo card — unchanged visual; hidden below md. */
function DealPromoLead({
  title,
  href,
  iconSrc,
  hrefLabel = "مشاهده همه",
  lede,
}: DealLeadPromo) {
  return (
    <Link
      href={href}
      className={cn(
        "group relative flex h-full min-h-[18.5rem] flex-col overflow-hidden rounded-[1.25rem]",
        "bg-[linear-gradient(170deg,#D02327_0%,#C01F23_48%,#A81B1F_100%)]",
        "px-3 py-5 text-white sm:min-h-[20.5rem] sm:rounded-[1.35rem] sm:px-3.5 sm:py-6",
        "shadow-[0_14px_32px_-18px_rgba(208,35,39,0.55)]",
        "transition-[transform,box-shadow] duration-300 ease-out",
        "hover:-translate-y-0.5 hover:shadow-[0_18px_40px_-18px_rgba(208,35,39,0.65)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#5E5F5E]",
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(90%_70%_at_50%_-5%,rgba(255,255,255,0.2),transparent_58%)]"
      />

      <p className="relative text-center text-[0.95rem] font-bold leading-snug tracking-tight sm:text-[1.05rem]">
        {title}
      </p>

      <div className="relative flex flex-1 items-center justify-center py-2 sm:py-3">
        {/* eslint-disable-next-line @next/next/no-img-element -- static public icon URL */}
        <img
          src={iconSrc}
          alt=""
          width={140}
          height={140}
          className={cn(
            "h-[6.5rem] w-[6.5rem] object-contain sm:h-[7.5rem] sm:w-[7.5rem]",
            "drop-shadow-[0_10px_20px_rgba(0,0,0,0.25)]",
            "transition-transform duration-500 ease-out group-hover:scale-[1.05]",
          )}
        />
      </div>

      <div className="relative mt-auto space-y-1.5 text-center">
        {lede ? (
          <p className="line-clamp-2 px-0.5 text-[11px] font-medium leading-relaxed text-white/75 sm:text-xs">
            {lede}
          </p>
        ) : null}
        <span className="inline-flex items-center justify-center gap-0.5 text-[13px] font-bold text-white sm:text-sm">
          {hrefLabel}
          <span className="transition-transform duration-300 group-hover:-translate-x-0.5">
            <ChevronLeft size="small" set="light" primaryColor="currentColor" />
          </span>
        </span>
      </div>
    </Link>
  );
}

function DealLeadSkeleton() {
  return (
    <div
      className={cn(
        "flex h-full min-h-[18.5rem] flex-col items-center justify-between rounded-[1.25rem]",
        "bg-[#D02327]/90 px-4 py-6 sm:min-h-[20.5rem] sm:rounded-[1.35rem]",
      )}
      aria-hidden
    >
      <div className="h-4 w-24 rounded bg-white/25" />
      <div className="h-24 w-24 rounded-full bg-white/15 sm:h-28 sm:w-28" />
      <div className="h-3.5 w-20 rounded bg-white/25" />
    </div>
  );
}

function DealStripShell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn(DEAL_STRIP_MOBILE, DEAL_STRIP_DESKTOP, className)}>
      {children}
    </div>
  );
}

export function ProductCarousel({
  products,
  isLoading,
  variant = "default",
  autoPlay = false,
  intervalMs = 3400,
  lead,
  headingId,
}: {
  products: ProductSummary[];
  isLoading?: boolean;
  variant?: "default" | "featured" | "deal";
  autoPlay?: boolean;
  intervalMs?: number;
  /** Lead promo panel for deal carousel (RTL visual start — pinned on desktop). */
  lead?: DealLeadPromo;
  headingId?: string;
}) {
  const isDeal = variant === "deal" && Boolean(lead);
  const cardWidth =
    variant === "featured"
      ? "w-[230px] sm:w-[270px]"
      : variant === "deal"
        ? "w-[167px] md:w-[196px]"
        : "w-[210px] sm:w-[250px]";
  const leadWidth = "w-[148px]";

  if (isLoading) {
    if (isDeal && lead) {
      return (
        <DealStripShell>
          <DealMobileHeader
            {...lead}
            hrefLabel="همه"
            headingId={headingId}
          />
          <div className="flex items-stretch gap-3 overflow-hidden px-5 sm:gap-3.5 sm:px-6 md:px-0">
            <div className={cn("hidden shrink-0 md:block", leadWidth)}>
              <DealLeadSkeleton />
            </div>
            <div className="flex min-w-0 flex-1 gap-3 overflow-hidden sm:gap-3.5">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className={cn("shrink-0", cardWidth)}>
                  <ProductCardSkeleton variant="deal" />
                </div>
              ))}
            </div>
          </div>
        </DealStripShell>
      );
    }

    return (
      <div className="flex gap-3 overflow-hidden sm:gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className={cn("shrink-0", cardWidth)}>
            <ProductCardSkeleton />
          </div>
        ))}
      </div>
    );
  }

  // Duplicate for seamless infinite feel when short lists — lead stays pinned once.
  const loop =
    products.length > 0 && products.length < 8
      ? [...products, ...products, ...products]
      : products.length >= 8
        ? [...products, ...products]
        : products;

  if (loop.length === 0) return null;

  if (isDeal && lead) {
    return (
      <DealStripShell>
        <DealMobileHeader {...lead} hrefLabel="همه" headingId={headingId} />

        {/* Lead pinned on RTL start (right) from md; mobile is header + product rail only */}
        <div className="flex items-stretch gap-3 px-5 sm:gap-3.5 sm:px-6 md:px-0">
          <div className={cn("hidden shrink-0 self-stretch md:block", leadWidth)}>
            <DealPromoLead {...lead} />
          </div>

          <div className="min-w-0 flex-1">
            <AutoCarousel
              autoPlay={autoPlay && products.length > 1}
              intervalMs={intervalMs}
              itemClassName={cardWidth}
              gapClass="gap-3 sm:gap-3.5"
              trackClassName="items-stretch pb-0.5"
              showControls={products.length > 2}
              controls="end"
              controlClassName={cn(
                "h-10 w-10 border-0 bg-white text-[#5E5F5E]",
                "shadow-[0_6px_18px_-6px_rgba(94,95,94,0.45)]",
                "hover:text-[#D02327]",
              )}
            >
              {loop.map((p, i) => (
                <ProductCard
                  key={`${p.id}-${i}`}
                  product={p}
                  variant="deal"
                  priority={isPlpLcpIndex(i, 2)}
                />
              ))}
            </AutoCarousel>
          </div>
        </div>
      </DealStripShell>
    );
  }

  return (
    <div
      className={cn(
        variant === "featured" &&
          "rounded-3xl bg-gradient-to-l from-secondary/80 to-transparent p-1 sm:p-2",
      )}
    >
      <AutoCarousel
        autoPlay={autoPlay && products.length > 1}
        intervalMs={intervalMs}
        itemClassName={cardWidth}
        gapClass="gap-3 sm:gap-4"
        trackClassName="pb-2"
        showControls={products.length > 2}
        controlClassName="h-11 w-11"
      >
        {loop.map((p, i) => (
          <ProductCard key={`${p.id}-${i}`} product={p} priority={isPlpLcpIndex(i, 2)} />
        ))}
      </AutoCarousel>
    </div>
  );
}
