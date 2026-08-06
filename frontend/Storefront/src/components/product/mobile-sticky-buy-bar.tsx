"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { Buy, Document, TickSquare } from "react-iconly";
import { Button } from "@/components/ui/button";
import {
  ADD_QTY_FALLBACK_MS,
  SoftQtyConfirm,
} from "@/components/product/soft-qty-confirm";
import { cn, formatNumber } from "@/lib/utils";
import type { ProductDetail } from "@/types/product";
import { useCartStore } from "@/store/cart-store";

type CartPhase = "idle" | "open" | "success";

/**
 * Fixed purchase bar for phones — sits above the mobile bottom nav.
 * Cart CTA soft-expands into qty + confirm; abandon → add 1.
 * Desktop is unaffected (lg:hidden via .mobile-dock).
 */
export function MobileStickyBuyBar({ product }: { product: ProductDetail }) {
  const addToCart = useCartStore((s) => s.addToCart);
  const addToQuote = useCartStore((s) => s.addToQuote);
  const [quoteFlash, setQuoteFlash] = useState(false);
  const [phase, setPhase] = useState<CartPhase>("idle");
  const [qty, setQty] = useState(1);
  const [reducedMotion, setReducedMotion] = useState(false);

  const phaseRef = useRef<CartPhase>("idle");
  const committedRef = useRef(false);
  const fallbackTimerRef = useRef<number | null>(null);
  const successTimerRef = useRef<number | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const labelId = useId();

  const hasPrice = product.base_price != null;
  const outOfStock = !product.availability;
  const hasDiscount =
    Boolean(product.discount_percent && product.discount_percent > 0) &&
    Boolean(product.original_price);

  const isOpen = phase === "open";
  const isSuccess = phase === "success";
  const isExpanded = isOpen || isSuccess;

  const summary = {
    id: product.id,
    sku: product.sku,
    name: product.name,
    thumbnail: product.thumbnail,
    base_price: product.base_price,
    original_price: product.original_price,
    discount_percent: product.discount_percent,
    stock_status: product.stock_status,
    availability: product.availability,
    is_original: product.is_original,
    category: product.category,
    brand: product.brand,
  };

  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  const clearTimers = useCallback(() => {
    if (fallbackTimerRef.current != null) {
      window.clearTimeout(fallbackTimerRef.current);
      fallbackTimerRef.current = null;
    }
    if (successTimerRef.current != null) {
      window.clearTimeout(successTimerRef.current);
      successTimerRef.current = null;
    }
  }, []);

  const finishSuccess = useCallback(() => {
    setPhase("success");
    phaseRef.current = "success";
    clearTimers();
    const hold = reducedMotion ? 500 : 2200;
    successTimerRef.current = window.setTimeout(() => {
      setPhase("idle");
      phaseRef.current = "idle";
      setQty(1);
      committedRef.current = false;
      successTimerRef.current = null;
    }, hold);
  }, [clearTimers, reducedMotion]);

  const commit = useCallback(
    (amount: number) => {
      if (committedRef.current) return;
      committedRef.current = true;
      const n = Math.max(1, Math.min(99, amount));
      addToCart(summary, n);
      finishSuccess();
    },
    // summary fields are stable per product mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [addToCart, finishSuccess, product.id],
  );

  const dismissWithoutConfirm = useCallback(() => {
    if (phaseRef.current !== "open") return;
    commit(1);
  }, [commit]);

  const openQty = useCallback(() => {
    if (outOfStock || !hasPrice) return;
    clearTimers();
    committedRef.current = false;
    setQty(1);
    setPhase("open");
    phaseRef.current = "open";
    fallbackTimerRef.current = window.setTimeout(() => {
      dismissWithoutConfirm();
    }, ADD_QTY_FALLBACK_MS);
  }, [clearTimers, dismissWithoutConfirm, hasPrice, outOfStock]);

  const confirm = useCallback(() => {
    if (phaseRef.current !== "open") return;
    commit(qty);
  }, [commit, qty]);

  // Outside tap / Escape while qty open
  useEffect(() => {
    if (phase !== "open") return;

    const onPointerDown = (e: PointerEvent) => {
      const el = rootRef.current;
      if (!el) return;
      if (e.target instanceof Node && !el.contains(e.target)) {
        dismissWithoutConfirm();
      }
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        dismissWithoutConfirm();
      }
    };

    document.addEventListener("pointerdown", onPointerDown, true);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown, true);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [dismissWithoutConfirm, phase]);

  useEffect(() => {
    return () => {
      clearTimers();
      if (phaseRef.current === "open" && !committedRef.current) {
        committedRef.current = true;
        addToCart(summary, 1);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleQuote = () => {
    if (outOfStock) return;
    addToQuote(summary, 1);
    setQuoteFlash(true);
    window.setTimeout(() => setQuoteFlash(false), 2500);
  };

  const expandMotion = reducedMotion
    ? "duration-0"
    : "duration-[320ms] ease-[cubic-bezier(0.22,1,0.36,1)]";

  const fadeMotion = reducedMotion
    ? "duration-75"
    : "duration-[250ms] ease-out";

  return (
    <div
      ref={rootRef}
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

      {/* Soft qty strip — expands upward above the price row */}
      {hasPrice ? (
        <div
          className={cn(
            "grid transition-[grid-template-rows]",
            expandMotion,
          )}
          style={{ gridTemplateRows: isExpanded ? "1fr" : "0fr" }}
          aria-hidden={!isExpanded}
        >
          <div className="min-h-0 overflow-hidden">
            <div
              className={cn(
                "border-b border-[#5E5F5E]/[0.06] bg-[#FAFAF9]/95 px-3.5 py-2.5 sm:px-4",
                "transition-[opacity,transform]",
                fadeMotion,
                isExpanded
                  ? "translate-y-0 opacity-100"
                  : "translate-y-1 opacity-0",
              )}
            >
              <div className="mx-auto max-w-lg">
                {isSuccess ? (
                  <Link
                    href="/cart"
                    className={cn(
                      "flex h-10 items-center justify-center gap-1.5",
                      "rounded-xl text-[13px] font-bold text-[#1a7a4c]",
                      "bg-[#1a7a4c]/[0.08]",
                    )}
                    role="status"
                    aria-live="polite"
                  >
                    <TickSquare
                      size="small"
                      set="bold"
                      primaryColor="currentColor"
                    />
                    اضافه شد — مشاهده سبد
                  </Link>
                ) : (
                  <SoftQtyConfirm
                    qty={qty}
                    onChange={setQty}
                    onConfirm={confirm}
                    variant="dock"
                    tabbable={isOpen}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <div className="px-3.5 py-2.5 sm:px-4">
        <div className="mx-auto flex max-w-lg items-center gap-3">
          <div
            className={cn(
              "min-w-0 flex-1 text-start transition-opacity",
              fadeMotion,
              isOpen && "opacity-55",
            )}
          >
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
                    <span className="text-[11px] text-muted-foreground line-through tnum">
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
            <Button
              size="lg"
              disabled={outOfStock || isExpanded}
              aria-expanded={isOpen}
              className={cn(
                "h-11 min-w-[9.5rem] shrink-0 gap-1.5 rounded-xl px-3.5 text-[12.5px] font-bold tracking-tight sm:min-w-[11rem] sm:px-4 sm:text-[13px]",
                "shadow-[0_12px_28px_-12px_rgba(208,35,39,0.65)]",
                "active:scale-[0.98] transition-[transform,opacity]",
                fadeMotion,
                isExpanded && "pointer-events-none opacity-40",
              )}
              onClick={openQty}
            >
              <Buy set="bold" size="small" />
              {outOfStock ? "ناموجود" : "افزودن به سبد خرید"}
            </Button>
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
