"use client";

import Link from "next/link";
import { ChevronLeft } from "react-iconly";
import { CategoryVisualIcon } from "@/components/ui/category-visual-icon";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatNumber } from "@/lib/utils";

/**
 * Soft industrial L1 category tile for mobile grids.
 * Matte workshop plaque + oversized icon roundel — shared by home and `/categories`.
 * Parents own the grid; this file owns surface / type / motion only.
 */
export function MobileCategoryCard({
  name,
  href,
  icon,
  count = null,
  showChevron = false,
  className,
}: {
  name: string;
  href: string;
  icon?: string | null;
  /** Live product count; null → soft “مشاهده دسته” hint. */
  count?: number | null;
  /** Trailing chevron — useful on single-column `/categories`. */
  showChevron?: boolean;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "group relative flex min-h-[5.65rem] items-center gap-3.5 overflow-hidden",
        "rounded-[1.35rem] pe-3.5 ps-3 py-3 text-start",
        /* Cool matte plaque — workshop steel, not porcelain slab */
        "bg-[linear-gradient(168deg,#FBFBFB_0%,#F2F2F3_42%,#E8E8EA_100%)]",
        "ring-1 ring-inset ring-[#5E5F5E]/[0.11]",
        "shadow-[0_1px_0_rgba(255,255,255,0.9)_inset,0_10px_22px_-16px_rgba(40,40,42,0.35)]",
        "transition-[transform,box-shadow,background] duration-200 ease-out",
        "active:scale-[0.975]",
        "hover:bg-[linear-gradient(168deg,#FFFFFF_0%,#F5F3F3_48%,#EDE8E8_100%)]",
        "hover:shadow-[0_1px_0_rgba(255,255,255,0.95)_inset,0_14px_28px_-14px_rgba(40,40,42,0.28),0_18px_36px_-22px_rgba(208,35,39,0.18)]",
        "hover:ring-[#5E5F5E]/[0.14]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 focus-visible:ring-offset-2",
        className,
      )}
    >
      {/* Soft paper grain (CSS-only, no image) */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.35] mix-blend-multiply"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, rgba(94,95,94,0.14) 1px, transparent 0)",
          backgroundSize: "7px 7px",
        }}
      />

      {/* Top lip highlight */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-l from-transparent via-white to-transparent"
      />

      {/* Brand ink tick — always present, strengthens on press/hover */}
      <span
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-y-3.5 start-0 w-[3px] rounded-e-full",
          "bg-[#D02327]/45",
          "transition-[background-color,box-shadow] duration-200",
          "group-hover:bg-[#D02327] group-hover:shadow-[0_0_12px_-2px_rgba(208,35,39,0.55)]",
          "group-active:bg-[#D02327]",
        )}
      />

      {/* Oversized icon roundel — primary visual weight */}
      <span
        className={cn(
          "relative grid h-[4.15rem] w-[4.15rem] shrink-0 place-items-center overflow-visible",
          "rounded-full",
          "bg-[radial-gradient(circle_at_42%_32%,#FFFFFF_0%,#F7F7F8_48%,#ECECEE_100%)]",
          "ring-[1.5px] ring-inset ring-white/90",
          "shadow-[inset_0_2px_4px_rgba(255,255,255,0.95),inset_0_-3px_6px_rgba(94,95,94,0.08),0_0_0_1px_rgba(94,95,94,0.1),0_10px_20px_-12px_rgba(40,40,42,0.45)]",
          "transition-[transform,box-shadow] duration-200 ease-out",
          "group-hover:scale-[1.06]",
          "group-hover:shadow-[inset_0_2px_4px_rgba(255,255,255,1),inset_0_-3px_6px_rgba(94,95,94,0.06),0_0_0_1px_rgba(208,35,39,0.16),0_14px_26px_-12px_rgba(208,35,39,0.28)]",
          "group-active:scale-[1.02]",
          "will-change-transform",
        )}
      >
        {/* Recessed floor under glyph */}
        <span
          aria-hidden
          className={cn(
            "pointer-events-none absolute inset-[14%] rounded-full",
            "bg-[radial-gradient(circle,rgba(94,95,94,0.09)_0%,transparent_70%)]",
            "transition-opacity duration-200",
            "group-hover:bg-[radial-gradient(circle,rgba(208,35,39,0.12)_0%,transparent_70%)]",
          )}
        />
        <CategoryVisualIcon
          icon={icon}
          size={34}
          overflowTop
          overflowScale={1.58}
          color="#5E5F5E"
          alt=""
          imgClassName="drop-shadow-[0_6px_14px_rgba(0,0,0,0.22)]"
        />
      </span>

      <span className="relative min-w-0 flex-1 pe-0.5">
        <span
          className={cn(
            "block overflow-hidden text-[15px] font-black leading-[1.35] tracking-[-0.015em] text-[#1a1a1a]",
            "line-clamp-2 break-words transition-colors duration-200",
            "group-hover:text-[#D02327]",
          )}
          title={name}
        >
          {name}
        </span>
        {count != null ? (
          <span
            className={cn(
              "mt-2 inline-flex max-w-full items-center rounded-md",
              "bg-[#5E5F5E]/[0.07] px-2 py-[3px]",
              "text-[10.5px] font-bold tabular-nums tracking-normal text-[#5E5F5E]/70",
              "ring-1 ring-inset ring-[#5E5F5E]/[0.06]",
              "transition-[background-color,color,ring-color] duration-200",
              "group-hover:bg-[#D02327]/[0.08] group-hover:text-[#D02327]/85 group-hover:ring-[#D02327]/15",
            )}
            aria-label={`${formatNumber(count)} محصول`}
          >
            {formatNumber(count)}
          </span>
        ) : (
          <span
            className={cn(
              "mt-2 inline-flex max-w-full items-center gap-1 rounded-md",
              "bg-[#5E5F5E]/[0.06] px-2 py-[3px]",
              "text-[10.5px] font-bold tracking-normal text-[#5E5F5E]/55",
              "ring-1 ring-inset ring-[#5E5F5E]/[0.05]",
              "transition-[background-color,color,ring-color] duration-200",
              "group-hover:bg-[#D02327]/[0.07] group-hover:text-[#D02327]/80 group-hover:ring-[#D02327]/12",
            )}
          >
            مشاهده دسته
          </span>
        )}
      </span>

      {showChevron ? (
        <span
          className={cn(
            "relative grid h-8 w-8 shrink-0 place-items-center rounded-full",
            "bg-white/80 text-[#5E5F5E]/40",
            "ring-1 ring-inset ring-[#5E5F5E]/[0.08]",
            "shadow-[inset_0_1px_0_rgba(255,255,255,0.95)]",
            "transition-[color,background-color,box-shadow,transform] duration-200",
            "group-hover:bg-[#D02327]/[0.1] group-hover:text-[#D02327] group-hover:ring-[#D02327]/18",
            "group-hover:translate-x-[-2px]",
          )}
        >
          <ChevronLeft size="small" set="light" primaryColor="currentColor" />
        </span>
      ) : null}
    </Link>
  );
}

export function MobileCategoryCardSkeleton({
  className,
}: {
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex min-h-[5.65rem] items-center gap-3.5 rounded-[1.35rem] pe-3.5 ps-3 py-3",
        "bg-[linear-gradient(168deg,#FBFBFB_0%,#F2F2F3_42%,#E8E8EA_100%)]",
        "ring-1 ring-inset ring-[#5E5F5E]/[0.1]",
        "shadow-[0_1px_0_rgba(255,255,255,0.9)_inset,0_10px_22px_-16px_rgba(40,40,42,0.28)]",
        className,
      )}
    >
      <Skeleton className="h-[4.15rem] w-[4.15rem] shrink-0 rounded-full" />
      <div className="min-w-0 flex-1 space-y-2.5">
        <Skeleton className="h-4 w-[78%] rounded-md" />
        <Skeleton className="h-5 w-9 rounded-md" />
      </div>
    </div>
  );
}
