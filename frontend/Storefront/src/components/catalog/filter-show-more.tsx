"use client";

import { useEffect, useState } from "react";
import { cn, toPersianDigits } from "@/lib/utils";

/** Initial visible rows/chips inside an open filter accordion (no panel max-height). */
export const FILTER_OPTION_PREVIEW = 20;

/** Brands accordion only — shorter preview before «نمایش بیشتر». */
export const FILTER_BRAND_PREVIEW = 5;

/** Collapse long filter option lists: first N, then «نمایش بیشتر» → all. */
export function useFilterShowMore(
  total: number,
  /** Reset collapsed state when this key changes (e.g. search query). */
  resetKey?: string | number,
  limit = FILTER_OPTION_PREVIEW,
) {
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setExpanded(false);
  }, [resetKey]);

  const showAll = expanded || total <= limit;
  const visibleCount = showAll ? total : limit;
  const canShowMore = total > limit && !expanded;

  return {
    visibleCount,
    canShowMore,
    remaining: Math.max(0, total - limit),
    showMore: () => setExpanded(true),
  };
}

export function FilterShowMoreButton({
  remaining,
  onClick,
  className,
}: {
  remaining: number;
  onClick: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "mt-2 flex min-h-10 w-full items-center justify-center gap-1.5 rounded-xl",
        "text-xs font-bold text-[#D02327] transition-colors",
        "hover:bg-[#D02327]/[0.08]",
        className,
      )}
    >
      <span>نمایش بیشتر</span>
      {remaining > 0 ? (
        <span className="tabular-nums text-[10px] font-bold text-[#5E5F5E]/70">
          ({toPersianDigits(remaining)}+)
        </span>
      ) : null}
    </button>
  );
}
