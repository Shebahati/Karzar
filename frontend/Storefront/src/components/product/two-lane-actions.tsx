"use client";

import Link from "next/link";
import { Buy, Call, Document, Plus } from "react-iconly";
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
 * Two-lane purchase:
 * - priced → cart qty live from Zustand (same source as product-card ATC)
 * - price-less → quote qty live from Zustand
 *
 * Compact density: denser qty/CTA chrome for the sticky buy card,
 * with clear vertical rhythm (not crushed).
 */
export function TwoLaneActions({
  product,
  onAdded,
}: {
  product: ProductDetail;
  onAdded?: (lane: "cart" | "quote") => void;
}) {
  const summary = toCartProductSummary(product);
  const cart = useProductCartQty(summary);
  const quote = useProductQuoteQty(summary);

  const hasPrice = product.base_price != null;
  const outOfStock = !product.availability;

  const handleFirstCartAdd = () => {
    cart.addOne();
    onAdded?.("cart");
  };

  const handleFirstQuoteAdd = () => {
    quote.addOne();
    onAdded?.("quote");
  };

  return (
    <div className="flex flex-col gap-3.5">
      {hasPrice ? (
        <>
          {!outOfStock && cart.inCart ? (
            <div className="flex items-center justify-between gap-3">
              <span className="text-[12px] font-medium text-steel">تعداد</span>
              <LiveQtyStepper
                qty={cart.qty}
                disabled={outOfStock}
                canIncrement={cart.canIncrement}
                onPlus={cart.increment}
                onMinus={cart.decrement}
              />
            </div>
          ) : null}

          {cart.inCart ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-success/10 px-3 py-2.5 text-[12px] text-success">
              <span className="font-medium">در سبد خرید است.</span>
              <Link
                href="/cart"
                className="font-bold underline-offset-2 hover:underline"
              >
                مشاهده سبد
              </Link>
            </div>
          ) : (
            <Button
              size="md"
              className={cn(
                "h-11 w-full rounded-xl text-[13px] font-bold tracking-tight",
                "shadow-[0_10px_24px_-14px_rgba(208,35,39,0.55)]",
              )}
              disabled={outOfStock}
              onClick={handleFirstCartAdd}
            >
              <Buy set="bold" size="small" />
              {outOfStock ? "ناموجود" : "افزودن به سبد خرید"}
            </Button>
          )}
        </>
      ) : (
        <>
          {!outOfStock && quote.inQuote ? (
            <div className="flex items-center justify-between gap-3">
              <span className="text-[12px] font-medium text-steel">تعداد</span>
              <LiveQtyStepper
                qty={quote.qty}
                disabled={outOfStock}
                canIncrement={quote.canIncrement}
                onPlus={quote.increment}
                onMinus={quote.decrement}
              />
            </div>
          ) : null}

          {quote.inQuote ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-success/10 px-3 py-2.5 text-[12px] text-success">
              <span className="font-medium">در سبد استعلام است.</span>
              <Link
                href="/quote"
                className="font-bold underline-offset-2 hover:underline"
              >
                مشاهده استعلام
              </Link>
            </div>
          ) : (
            <Button
              size="md"
              variant="outline"
              className={cn(
                "h-11 w-full rounded-xl text-[13px] font-bold tracking-tight",
                "border-steel/20 bg-white text-foreground",
                "hover-fine:bg-secondary hover-fine:ring-steel/25",
              )}
              disabled={outOfStock}
              onClick={handleFirstQuoteAdd}
            >
              <Document set="bold" size="small" />
              {outOfStock ? "ناموجود" : "افزودن به استعلام"}
            </Button>
          )}

          <p className="flex items-start gap-1.5 text-[11px] leading-5 text-muted-foreground">
            <Call size="small" set="light" />
            برای مشاوره تخصصی از صفحه{" "}
            <Link
              href="/contact"
              className="font-medium text-foreground underline-offset-2 hover:underline"
            >
              تماس با ما
            </Link>{" "}
            پیام بگذارید.
          </p>
        </>
      )}
    </div>
  );
}

function LiveQtyStepper({
  qty,
  disabled,
  canIncrement,
  onPlus,
  onMinus,
}: {
  qty: number;
  disabled: boolean;
  canIncrement: boolean;
  onPlus: () => void;
  onMinus: () => void;
}) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-0.5 rounded-lg bg-white p-0.5",
        "ring-1 ring-[#D02327]/20",
        "shadow-[0_4px_14px_-10px_rgba(94,95,94,0.45)]",
      )}
    >
      <button
        type="button"
        aria-label="کاهش"
        disabled={disabled}
        onClick={onMinus}
        className={cn(
          "grid h-8 w-8 place-items-center rounded-md",
          "text-base font-medium leading-none text-[#5E5F5E]",
          "transition-colors hover:bg-[#D02327]/[0.08] hover:text-[#D02327]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35",
          "active:scale-95 disabled:opacity-35",
        )}
      >
        −
      </button>
      <span
        className="min-w-8 select-none text-center text-[13px] font-bold tabular-nums text-foreground tnum"
        aria-live="polite"
        aria-atomic="true"
      >
        {formatNumber(qty)}
      </span>
      <button
        type="button"
        aria-label="افزایش"
        disabled={disabled || !canIncrement || qty >= CART_QTY_MAX}
        onClick={onPlus}
        className={cn(
          "grid h-8 w-8 place-items-center rounded-md",
          "text-[#5E5F5E]",
          "transition-colors hover:bg-[#D02327]/[0.08] hover:text-[#D02327]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35",
          "active:scale-95 disabled:opacity-35",
        )}
      >
        <Plus size="small" set="bold" primaryColor="currentColor" />
      </button>
    </div>
  );
}

