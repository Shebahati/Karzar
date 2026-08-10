"use client";

import Link from "next/link";
import { useId, useState } from "react";
import { Buy, Document } from "react-iconly";
import { Button } from "@/components/ui/button";
import { cn, formatNumber } from "@/lib/utils";
import {
  CART_QTY_MAX,
  toCartProductSummary,
  useProductCartQty,
  useProductQuoteQty,
} from "@/components/product/use-product-cart-qty";
import type { ProductDetail } from "@/types/product";

/**
 * Fixed purchase bar for phones — sits above the mobile bottom nav.
 * Cart CTA transforms in-place into − / qty / + (same pattern as product-card ATC).
 * Qty is live from the cart store — no separate confirm strip above.
 */
export function MobileStickyBuyBar({ product }: { product: ProductDetail }) {
  const summary = toCartProductSummary(product);
  const cart = useProductCartQty(summary);
  const quote = useProductQuoteQty(summary);
  const [quoteFlash, setQuoteFlash] = useState(false);
  const labelId = useId();

  const hasPrice = product.base_price != null;
  const outOfStock = !product.availability;
  const hasDiscount =
    Boolean(product.discount_percent && product.discount_percent > 0) &&
    Boolean(product.original_price);

  const handleQuote = () => {
    if (outOfStock) return;
    quote.addOne();
    setQuoteFlash(true);
    window.setTimeout(() => setQuoteFlash(false), 2500);
  };

  const inCart = hasPrice && cart.inCart;
  const inQuote = !hasPrice && quote.inQuote;

  return (
    <div
      className="mobile-dock"
      role="region"
      aria-label="خرید سریع محصول"
      aria-labelledby={labelId}
    >
      <span id={labelId} className="sr-only">
        خرید سریع محصول
      </span>

      {product.low_stock && !outOfStock ? (
        <p className="border-b border-[#D02327]/15 bg-[#D02327]/[0.06] px-4 py-1.5 text-center text-[11px] font-semibold text-primary">
          موجودی محدود — همین حالا سفارش دهید
        </p>
      ) : null}

      <div className="px-3.5 py-2.5 sm:px-4">
        <div className="mx-auto flex max-w-lg items-center gap-3">
          <div className="min-w-0 flex-1 text-start">
            {quoteFlash ? (
              <Link
                href="/quote"
                className="block text-[12px] font-bold text-success"
              >
                اضافه شد — مشاهده
              </Link>
            ) : hasPrice ? (
              <>
                {hasDiscount ? (
                  <div className="mb-0.5 flex flex-wrap items-center gap-1.5">
                    <span className="text-[11px] font-medium text-[#D02327]/55 line-through tnum">
                      {formatNumber(product.original_price)}
                    </span>
                    <span className="rounded-md bg-[#D02327] px-1.5 py-0.5 text-[10px] font-bold leading-none text-white tnum">
                      ٪{formatNumber(product.discount_percent)}
                    </span>
                  </div>
                ) : null}
                <p className="truncate text-[15px] font-bold leading-tight tracking-tight text-foreground tnum sm:text-[16px]">
                  {formatNumber(product.base_price)}
                  <span className="ms-1 text-[11px] font-semibold text-steel">
                    تومان
                  </span>
                </p>
              </>
            ) : (
              <p className="truncate text-[13px] font-bold text-primary">
                استعلام قیمت
              </p>
            )}
          </div>

          {hasPrice ? (
            <DockCartCta
              disabled={outOfStock}
              qty={cart.qty}
              inCart={inCart}
              canIncrement={cart.canIncrement}
              onAdd={cart.addOne}
              onPlus={cart.increment}
              onMinus={cart.decrement}
            />
          ) : inQuote ? (
            <DockQtyStepper
              qty={quote.qty}
              disabled={outOfStock}
              canIncrement={quote.canIncrement}
              onPlus={quote.increment}
              onMinus={quote.decrement}
              ariaLabel="تعداد استعلام"
            />
          ) : (
            <Button
              size="lg"
              variant="outline"
              disabled={outOfStock}
              className={cn(
                "h-11 shrink-0 gap-1.5 rounded-xl border-foreground/15 bg-card px-3.5",
                "text-[13px] font-bold text-foreground",
              )}
              onClick={handleQuote}
            >
              <Document set="bold" size="small" />
              {outOfStock ? "ناموجود" : "افزودن به استعلام"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function DockCartCta({
  disabled,
  qty,
  inCart,
  canIncrement,
  onAdd,
  onPlus,
  onMinus,
}: {
  disabled: boolean;
  qty: number;
  inCart: boolean;
  canIncrement: boolean;
  onAdd: () => void;
  onPlus: () => void;
  onMinus: () => void;
}) {
  return (
    <div
      role="group"
      aria-label="افزودن به سبد خرید"
      className={cn(
        "relative flex h-11 w-[9.5rem] shrink-0 items-center overflow-hidden rounded-xl sm:w-[11rem]",
        "transition-[background-color,box-shadow] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]",
        "motion-reduce:transition-none",
        inCart
          ? cn(
              "bg-white",
              "ring-1 ring-[#D02327]/20",
              "shadow-[0_8px_20px_-12px_rgba(94,95,94,0.45)]",
            )
          : cn(
              "bg-[#D02327]",
              "shadow-[0_12px_28px_-12px_rgba(208,35,39,0.65)]",
            ),
      )}
    >
      <button
        type="button"
        disabled={disabled || inCart}
        aria-label="افزودن به سبد خرید"
        aria-expanded={inCart}
        tabIndex={inCart ? -1 : 0}
        onClick={onAdd}
        className={cn(
          "absolute inset-0 inline-flex items-center justify-center gap-1.5 px-3.5",
          "text-[12.5px] font-bold tracking-tight text-white sm:px-4 sm:text-[13px]",
          "transition-[opacity,transform] duration-200 ease-out",
          "motion-reduce:transition-none",
          "hover:bg-[#b81e23] active:scale-[0.98]",
          "disabled:pointer-events-none",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50",
          inCart
            ? "pointer-events-none scale-95 opacity-0"
            : "scale-100 opacity-100",
        )}
      >
        <Buy set="bold" size="small" />
        {disabled ? "ناموجود" : "افزودن به سبد خرید"}
      </button>

      <div
        className={cn(
          "flex h-full w-full items-center justify-between px-1",
          "transition-opacity duration-200 ease-out",
          "motion-reduce:transition-none",
          inCart ? "relative opacity-100" : "pointer-events-none absolute inset-0 opacity-0",
        )}
        aria-hidden={!inCart}
      >
        <DockStepperButtons
          qty={qty}
          disabled={disabled}
          canIncrement={canIncrement}
          tabbable={inCart}
          onPlus={onPlus}
          onMinus={onMinus}
        />
      </div>
    </div>
  );
}

function DockQtyStepper({
  qty,
  disabled,
  canIncrement,
  onPlus,
  onMinus,
  ariaLabel,
}: {
  qty: number;
  disabled: boolean;
  canIncrement: boolean;
  onPlus: () => void;
  onMinus: () => void;
  ariaLabel: string;
}) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={cn(
        "flex h-11 w-[9.5rem] shrink-0 items-center justify-between rounded-xl bg-white px-1 sm:w-[11rem]",
        "ring-1 ring-[#D02327]/20",
        "shadow-[0_8px_20px_-12px_rgba(94,95,94,0.45)]",
      )}
    >
      <DockStepperButtons
        qty={qty}
        disabled={disabled}
        canIncrement={canIncrement}
        tabbable
        onPlus={onPlus}
        onMinus={onMinus}
      />
    </div>
  );
}

function DockStepperButtons({
  qty,
  disabled,
  canIncrement,
  tabbable,
  onPlus,
  onMinus,
}: {
  qty: number;
  disabled: boolean;
  canIncrement: boolean;
  tabbable: boolean;
  onPlus: () => void;
  onMinus: () => void;
}) {
  const tab = tabbable ? 0 : -1;
  return (
    <>
      <button
        type="button"
        aria-label="کاهش تعداد"
        disabled={disabled}
        tabIndex={tab}
        onClick={onMinus}
        className={cn(
          "grid h-9 w-9 shrink-0 place-items-center rounded-lg",
          "text-[17px] font-medium leading-none text-[#5E5F5E]",
          "transition-colors hover:bg-[#D02327]/[0.08] hover:text-[#D02327]",
          "active:scale-95",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/30",
          "disabled:opacity-35",
        )}
      >
        −
      </button>

      <span
        className="min-w-[1.5rem] select-none text-center text-[14px] font-bold tabular-nums text-[#1a1a1a] tnum"
        aria-live="polite"
        aria-atomic="true"
      >
        {formatNumber(qty)}
      </span>

      <button
        type="button"
        aria-label="افزایش تعداد"
        disabled={disabled || !canIncrement || qty >= CART_QTY_MAX}
        tabIndex={tab}
        onClick={onPlus}
        className={cn(
          "grid h-9 w-9 shrink-0 place-items-center rounded-lg",
          "text-[17px] font-medium leading-none text-[#5E5F5E]",
          "transition-colors hover:bg-[#D02327]/[0.08] hover:text-[#D02327]",
          "active:scale-95",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/30",
          "disabled:opacity-35",
        )}
      >
        +
      </button>
    </>
  );
}

