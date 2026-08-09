"use client";

import { Buy } from "react-iconly";
import { cn, formatNumber } from "@/lib/utils";
import {
  CART_QTY_MAX,
  useProductCartQty,
} from "@/components/product/use-product-cart-qty";
import type { ProductSummary } from "@/types/product";

/** Expanded qty pill — lives in its own footer row; never fights price. */
const EXPANDED_W = "w-[6.5rem]";

/**
 * Product-card add-to-cart (in-flow, dedicated footer row):
 * - First tap → add 1 + expand to − / qty / +
 * - + / − update the cart immediately (no confirm tick)
 * - Stays open while this product remains in the cart
 * - Always h-8; collapsed = cart chip, expanded = qty pill, both end-aligned
 * - Width animates within the ATC row only — never lifts over the image
 */
export function CardAddToCartCta({
  product,
  disabled = false,
  onAdded,
  className,
}: {
  product: ProductSummary;
  disabled?: boolean;
  onAdded?: (qty: number) => void;
  className?: string;
}) {
  const { qty, inCart, addOne, increment, decrement, canIncrement } =
    useProductCartQty(product);

  const stop = (e: React.SyntheticEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const onFirstAdd = (e: React.MouseEvent) => {
    stop(e);
    if (disabled) return;
    addOne();
    onAdded?.(1);
  };

  const onPlus = (e: React.MouseEvent) => {
    stop(e);
    if (disabled || !canIncrement) return;
    increment();
  };

  const onMinus = (e: React.MouseEvent) => {
    stop(e);
    if (disabled) return;
    decrement();
  };

  return (
    <div
      role="group"
      aria-label="افزودن به سبد خرید"
      className={cn("flex h-8 w-full shrink-0 items-center justify-end", className)}
      onClick={stop}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <div
        className={cn(
          "relative flex h-8 items-center overflow-hidden rounded-lg",
          "transition-[width,background-color,box-shadow] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]",
          "motion-reduce:transition-none",
          inCart
            ? cn(
                EXPANDED_W,
                "bg-white",
                "ring-1 ring-[#D02327]/20",
                "shadow-[0_4px_14px_-10px_rgba(94,95,94,0.45)]",
              )
            : cn(
                "w-8",
                "bg-[#D02327]",
                "shadow-[0_6px_14px_-10px_rgba(208,35,39,0.55)]",
              ),
        )}
      >
        {/* Idle — compact cart chip */}
        <button
          type="button"
          onClick={onFirstAdd}
          disabled={disabled || inCart}
          aria-label="افزودن به سبد خرید"
          aria-expanded={inCart}
          tabIndex={inCart ? -1 : 0}
          className={cn(
            "absolute inset-0 grid place-items-center text-white",
            "transition-[opacity,transform] duration-200 ease-out",
            "motion-reduce:transition-none",
            "hover:bg-[#b81e23] active:scale-95",
            "disabled:pointer-events-none",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50",
            inCart
              ? "pointer-events-none scale-75 opacity-0"
              : "scale-100 opacity-100",
          )}
        >
          <Buy size="small" set="bold" primaryColor="currentColor" />
        </button>

        {/* Expanded — live cart qty stepper (no confirm) */}
        <div
          className={cn(
            "flex h-full w-full items-center justify-between px-0.5",
            "transition-opacity duration-200 ease-out",
            "motion-reduce:transition-none",
            inCart ? "relative opacity-100" : "pointer-events-none absolute inset-0 opacity-0",
          )}
          aria-hidden={!inCart}
        >
          <button
            type="button"
            aria-label="کاهش تعداد"
            disabled={disabled}
            tabIndex={inCart ? 0 : -1}
            onClick={onMinus}
            className={cn(
              "grid h-7 w-7 shrink-0 place-items-center rounded-md",
              "text-[15px] font-medium leading-none text-[#5E5F5E]",
              "transition-colors hover:bg-[#D02327]/[0.08] hover:text-[#D02327]",
              "active:scale-95",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/30",
              "disabled:opacity-35",
            )}
          >
            −
          </button>

          <span
            className="min-w-[1.25rem] select-none text-center text-[12px] font-bold tabular-nums text-[#1a1a1a] tnum"
            aria-live="polite"
            aria-atomic="true"
          >
            {formatNumber(qty)}
          </span>

          <button
            type="button"
            aria-label="افزایش تعداد"
            disabled={disabled || qty >= CART_QTY_MAX}
            tabIndex={inCart ? 0 : -1}
            onClick={onPlus}
            className={cn(
              "grid h-7 w-7 shrink-0 place-items-center rounded-md",
              "text-[15px] font-medium leading-none text-[#5E5F5E]",
              "transition-colors hover:bg-[#D02327]/[0.08] hover:text-[#D02327]",
              "active:scale-95",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/30",
              "disabled:opacity-35",
            )}
          >
            +
          </button>
        </div>
      </div>
    </div>
  );
}
