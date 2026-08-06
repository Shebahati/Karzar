"use client";

import Link from "next/link";
import { ChevronLeft } from "react-iconly";
import { CategoryVisualIcon } from "@/components/ui/category-visual-icon";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatNumber } from "@/lib/utils";

/**
 * Soft-premium L1 category tile for mobile grids.
 * Shared chrome for `/categories` and home mobile categories — keep layout grids
 * in the parents; only upgrade surface / icon well / type here.
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
        "group relative flex min-h-[4.75rem] items-center gap-3 overflow-visible",
        "rounded-[1.15rem] px-3 py-3 text-start",
        /* Soft wash — not flat slab, not Digikala white card */
        "bg-[linear-gradient(145deg,#FFFFFF_0%,#F7F7F7_48%,#F1F1F1_100%)]",
        "ring-1 ring-inset ring-[#5E5F5E]/[0.07]",
        "shadow-[0_1px_1px_rgba(94,95,94,0.04),0_10px_28px_-18px_rgba(94,95,94,0.22)]",
        "transition-[transform,box-shadow,background] duration-300 ease-out",
        "active:scale-[0.985]",
        "hover:bg-[linear-gradient(145deg,#FFFFFF_0%,#F9F6F6_52%,#F3EEEE_100%)]",
        "hover:shadow-[0_2px_4px_rgba(94,95,94,0.05),0_14px_32px_-16px_rgba(208,35,39,0.18)]",
        "hover:ring-primary/18",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 focus-visible:ring-offset-2",
        className,
      )}
    >
      {/* Soft top sheen */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-1/2 rounded-t-[1.15rem] bg-gradient-to-b from-white/70 to-transparent"
      />

      {/* Brand accent — hover/active only */}
      <span
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-y-2 start-0 w-[3px] rounded-full",
          "bg-gradient-to-b from-primary/0 via-primary to-primary/0",
          "opacity-0 transition-opacity duration-300",
          "group-hover:opacity-90 group-active:opacity-100",
        )}
      />

      {/* Icon well */}
      <span
        className={cn(
          "relative grid h-[3.25rem] w-[3.25rem] shrink-0 place-items-center overflow-visible",
          "rounded-[1.05rem]",
          "bg-[linear-gradient(160deg,#FFFFFF_0%,#F5F5F5_100%)]",
          "ring-1 ring-inset ring-[#5E5F5E]/[0.08]",
          "shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_6px_16px_-10px_rgba(94,95,94,0.35)]",
          "transition-[transform,box-shadow,ring-color] duration-300 ease-out",
          "group-hover:scale-[1.04]",
          "group-hover:ring-primary/20",
          "group-hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.95),0_10px_20px_-10px_rgba(208,35,39,0.22)]",
        )}
      >
        <span
          aria-hidden
          className="pointer-events-none absolute inset-[3px] rounded-[0.85rem] bg-gradient-to-br from-white/90 via-transparent to-[#5E5F5E]/[0.04]"
        />
        <CategoryVisualIcon
          icon={icon}
          size={30}
          overflowTop
          overflowScale={1.42}
          color="#5E5F5E"
          alt=""
          imgClassName="drop-shadow-[0_4px_10px_rgba(0,0,0,0.16)]"
        />
      </span>

      <span className="relative min-w-0 flex-1">
        <span
          className={cn(
            "block text-[13.5px] font-extrabold leading-[1.45] tracking-tight text-foreground",
            "line-clamp-2 transition-colors duration-300",
            "group-hover:text-primary sm:text-sm",
          )}
        >
          {name}
        </span>
        {count != null ? (
          <span className="mt-1 block text-[11px] font-semibold tabular-nums text-[#5E5F5E]/65">
            {formatNumber(count)} محصول
          </span>
        ) : (
          <span className="mt-1 block text-[11px] font-semibold text-[#5E5F5E]/50">
            مشاهده دسته
          </span>
        )}
      </span>

      {showChevron ? (
        <span
          className={cn(
            "relative grid h-8 w-8 shrink-0 place-items-center rounded-full",
            "bg-white/60 text-[#5E5F5E]/45 ring-1 ring-inset ring-[#5E5F5E]/[0.06]",
            "transition-[color,background-color,opacity] duration-300",
            "group-hover:bg-primary/[0.08] group-hover:text-primary group-hover:ring-primary/15",
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
        "flex min-h-[4.75rem] items-center gap-3 rounded-[1.15rem] px-3 py-3",
        "bg-[linear-gradient(145deg,#FFFFFF_0%,#F7F7F7_48%,#F1F1F1_100%)]",
        "ring-1 ring-inset ring-[#5E5F5E]/[0.06]",
        className,
      )}
    >
      <Skeleton className="h-[3.25rem] w-[3.25rem] shrink-0 rounded-[1.05rem]" />
      <div className="min-w-0 flex-1 space-y-2">
        <Skeleton className="h-3.5 w-[72%] rounded-full" />
        <Skeleton className="h-2.5 w-14 rounded-full" />
      </div>
    </div>
  );
}
