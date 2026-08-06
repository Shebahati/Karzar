"use client";

import { TickSquare } from "react-iconly";
import { cn, formatNumber } from "@/lib/utils";

export const ADD_QTY_FALLBACK_MS = 4000;
export const ADD_QTY_MAX = 99;

type SoftQtyConfirmProps = {
  qty: number;
  onChange: (qty: number) => void;
  onConfirm: () => void;
  /** `card` = compact footer chip; `dock` = premium sticky-bar strip. */
  variant?: "card" | "dock";
  /** Allow focus while the parent expander is open. */
  tabbable?: boolean;
  className?: string;
};

/**
 * Shared minimal qty stepper + red confirm — used by product-card expand
 * and the mobile PDP sticky buy bar.
 */
export function SoftQtyConfirm({
  qty,
  onChange,
  onConfirm,
  variant = "card",
  tabbable = true,
  className,
}: SoftQtyConfirmProps) {
  const isDock = variant === "dock";
  const tab = tabbable ? 0 : -1;

  const bump = (delta: number) => {
    onChange(Math.max(1, Math.min(ADD_QTY_MAX, qty + delta)));
  };

  return (
    <div
      className={cn(
        "flex w-full items-center",
        isDock ? "gap-2.5 px-0.5" : "gap-1.5 px-1.5",
        className,
      )}
    >
      <span
        className={cn(
          "shrink-0 select-none font-semibold tracking-tight text-[#5E5F5E]",
          isDock ? "text-[12px]" : "text-[11px]",
        )}
        aria-hidden
      >
        تعداد
      </span>

      <div
        className={cn(
          "inline-flex min-w-0 flex-1 items-center justify-center",
          isDock ? "gap-1" : "gap-0.5",
        )}
      >
        <button
          type="button"
          aria-label="کاهش تعداد"
          tabIndex={tab}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            bump(-1);
          }}
          className={cn(
            "grid shrink-0 place-items-center rounded-lg",
            "font-medium leading-none text-[#5E5F5E]",
            "transition-colors hover:bg-[#D02327]/[0.08] hover:text-[#D02327]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/30",
            "active:scale-95",
            isDock
              ? "h-10 w-10 text-[18px]"
              : "h-8 w-8 text-[15px]",
          )}
        >
          −
        </button>

        <span
          className={cn(
            "select-none text-center font-bold tabular-nums text-[#1a1a1a] tnum",
            isDock ? "min-w-[2rem] text-[15px]" : "min-w-[1.5rem] text-[13px]",
          )}
          aria-live="polite"
          aria-atomic="true"
        >
          {formatNumber(qty)}
        </span>

        <button
          type="button"
          aria-label="افزایش تعداد"
          tabIndex={tab}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            bump(1);
          }}
          className={cn(
            "grid shrink-0 place-items-center rounded-lg",
            "font-medium leading-none text-[#5E5F5E]",
            "transition-colors hover:bg-[#D02327]/[0.08] hover:text-[#D02327]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/30",
            "active:scale-95",
            isDock
              ? "h-10 w-10 text-[18px]"
              : "h-8 w-8 text-[16px]",
          )}
        >
          +
        </button>
      </div>

      <button
        type="button"
        aria-label="تأیید و افزودن به سبد خرید"
        tabIndex={tab}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onConfirm();
        }}
        className={cn(
          "shrink-0 inline-flex items-center justify-center gap-1",
          "bg-[#D02327] text-white font-bold",
          "shadow-[0_8px_18px_-12px_rgba(208,35,39,0.7)]",
          "transition-[transform,background-color,box-shadow]",
          "hover:bg-[#b81e23] hover:shadow-[0_10px_22px_-12px_rgba(208,35,39,0.75)]",
          "active:scale-[0.97]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/40",
          isDock
            ? "h-10 min-w-[4.75rem] rounded-xl px-3.5 text-[12.5px]"
            : "h-8 w-8 rounded-lg",
        )}
      >
        {isDock ? (
          "تأیید"
        ) : (
          <TickSquare size="small" set="bold" primaryColor="currentColor" />
        )}
      </button>
    </div>
  );
}
