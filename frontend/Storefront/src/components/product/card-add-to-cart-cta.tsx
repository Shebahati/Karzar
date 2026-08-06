"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { usePathname } from "next/navigation";
import { Buy, TickSquare } from "react-iconly";
import {
  ADD_QTY_FALLBACK_MS,
  SoftQtyConfirm,
} from "@/components/product/soft-qty-confirm";
import { useMotionSafe } from "@/lib/use-motion-safe";
import { cn } from "@/lib/utils";
import { useCartStore } from "@/store/cart-store";
import type { ProductSummary } from "@/types/product";

/** @deprecated Prefer ADD_QTY_FALLBACK_MS — kept for any external imports. */
export const CARD_ADD_FALLBACK_MS = ADD_QTY_FALLBACK_MS;

const SUCCESS_MS = 1100;

type Phase = "idle" | "open" | "success";

type DismissFn = () => void;
let activeDismiss: DismissFn | null = null;

function claimActive(dismiss: DismissFn) {
  if (activeDismiss && activeDismiss !== dismiss) activeDismiss();
  activeDismiss = dismiss;
}

function releaseActive(dismiss: DismissFn) {
  if (activeDismiss === dismiss) activeDismiss = null;
}

/** True when the user prefers reduced motion (all viewports). */
function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return reduced;
}

/**
 * Product-card add-to-cart CTA:
 * soft expand → qty stepper → confirm.
 * Abandon without confirm → add 1 once.
 */
export function CardAddToCartCta({
  product,
  disabled = false,
  onAdded,
  className,
}: {
  product: ProductSummary;
  disabled?: boolean;
  /** Called after a successful commit (confirm or fallback). */
  onAdded?: (qty: number) => void;
  className?: string;
}) {
  const addToCart = useCartStore((s) => s.addToCart);
  const pathname = usePathname();
  const motionSafe = useMotionSafe();
  const reducedMotion = usePrefersReducedMotion();
  const rootRef = useRef<HTMLDivElement>(null);
  const committedRef = useRef(false);
  const phaseRef = useRef<Phase>("idle");
  const fallbackTimerRef = useRef<number | null>(null);
  const successTimerRef = useRef<number | null>(null);
  const dismissImplRef = useRef<DismissFn>(() => {});
  const dismissStable = useCallback(() => {
    dismissImplRef.current();
  }, []);
  const [phase, setPhase] = useState<Phase>("idle");
  const [qty, setQty] = useState(1);
  const labelId = useId();

  const isOpen = phase === "open";
  const isSuccess = phase === "success";
  const isExpanded = isOpen || isSuccess;

  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

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
    releaseActive(dismissStable);
    const hold = reducedMotion ? 400 : SUCCESS_MS;
    successTimerRef.current = window.setTimeout(() => {
      setPhase("idle");
      phaseRef.current = "idle";
      setQty(1);
      committedRef.current = false;
      successTimerRef.current = null;
    }, hold);
  }, [clearTimers, dismissStable, reducedMotion]);

  const commit = useCallback(
    (amount: number) => {
      if (committedRef.current) return;
      committedRef.current = true;
      const n = Math.max(1, Math.min(99, amount));
      addToCart(product, n);
      onAdded?.(n);
      finishSuccess();
    },
    [addToCart, finishSuccess, onAdded, product],
  );

  const dismissWithoutConfirm = useCallback(() => {
    if (phaseRef.current !== "open") return;
    commit(1);
  }, [commit]);

  useEffect(() => {
    dismissImplRef.current = dismissWithoutConfirm;
  }, [dismissWithoutConfirm]);

  const open = useCallback(() => {
    if (disabled) return;
    clearTimers();
    committedRef.current = false;
    setQty(1);
    setPhase("open");
    phaseRef.current = "open";
    claimActive(dismissStable);
    fallbackTimerRef.current = window.setTimeout(() => {
      dismissStable();
    }, ADD_QTY_FALLBACK_MS);
  }, [clearTimers, disabled, dismissStable]);

  const confirm = useCallback(() => {
    if (phaseRef.current !== "open") return;
    commit(qty);
  }, [commit, qty]);

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
    if (phase !== "open") return;
    const el = rootRef.current;
    if (!el) return;

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry && entry.intersectionRatio < 0.35) {
          dismissWithoutConfirm();
        }
      },
      { threshold: [0, 0.35, 1] },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [dismissWithoutConfirm, phase]);

  const pathAtOpen = useRef(pathname);
  useEffect(() => {
    if (phase === "open") pathAtOpen.current = pathname;
  }, [phase, pathname]);

  useEffect(() => {
    if (phase !== "open") return;
    if (pathname !== pathAtOpen.current) dismissWithoutConfirm();
  }, [dismissWithoutConfirm, pathname, phase]);

  useEffect(() => {
    return () => {
      clearTimers();
      releaseActive(dismissStable);
      if (phaseRef.current === "open" && !committedRef.current) {
        committedRef.current = true;
        addToCart(product, 1);
        onAdded?.(1);
      }
    };
    // Intentionally once per card mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dismissStable]);

  const stop = (e: React.SyntheticEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  /**
   * Motion tiers:
   * - reduced → near-instant
   * - mobile → soft 240ms ease-out
   * - desktop motionSafe → richer 320ms ease
   */
  const shellMotion = reducedMotion
    ? "duration-0"
    : motionSafe
      ? "duration-[320ms] ease-[cubic-bezier(0.22,1,0.36,1)]"
      : "duration-[240ms] ease-out";

  const contentMotion = reducedMotion
    ? "duration-75"
    : motionSafe
      ? "duration-[280ms] ease-[cubic-bezier(0.22,1,0.36,1)]"
      : "duration-200 ease-out";

  return (
    <>
      {/* In-flow spacer so price row does not reflow on expand */}
      <div className="pointer-events-none h-9 w-9 shrink-0" aria-hidden />

      <div
        ref={rootRef}
        role="group"
        aria-labelledby={labelId}
        data-card-cta-open={isExpanded ? "" : undefined}
        className={cn(
          "absolute inset-0 z-20 flex items-end",
          !isExpanded && "pointer-events-none",
          className,
        )}
        onClick={stop}
        onKeyDown={(e) => e.stopPropagation()}
        aria-expanded={isOpen}
      >
        <span id={labelId} className="sr-only">
          انتخاب تعداد و تأیید افزودن به سبد
        </span>

        <div
          className={cn(
            "relative ms-auto flex items-center overflow-hidden",
            /* Size/shape animate; bg snaps so red never bleeds under cream */
            "transition-[width,max-width,height,border-radius,box-shadow,opacity]",
            shellMotion,
            isExpanded
              ? cn(
                  "h-full w-full max-w-full rounded-xl",
                  /* Opaque solid — matches card cream/white; no alpha wash */
                  "bg-[#FAFAF9]",
                  "ring-1 ring-[#5E5F5E]/[0.08]",
                  "shadow-[0_6px_20px_-14px_rgba(94,95,94,0.35)]",
                )
              : cn(
                  "pointer-events-auto h-9 w-9 max-w-9 rounded-lg",
                  "bg-[#D02327]",
                  "shadow-[0_8px_18px_-12px_rgba(208,35,39,0.55)]",
                  !reducedMotion &&
                    "hover:shadow-[0_10px_22px_-12px_rgba(208,35,39,0.65)]",
                ),
          )}
        >
          {/* Idle — cart affordance (hidden hard while open so red cannot show through) */}
          <button
            type="button"
            onClick={(e) => {
              stop(e);
              open();
            }}
            disabled={disabled || isExpanded}
            aria-label="افزودن به سبد خرید"
            aria-expanded={false}
            tabIndex={isExpanded ? -1 : 0}
            className={cn(
              "absolute inset-0 grid place-items-center text-white",
              "transition-[opacity,transform]",
              contentMotion,
              isExpanded
                ? "pointer-events-none invisible scale-75 opacity-0"
                : "visible scale-100 opacity-100",
              "hover:bg-[#b81e23] active:scale-95",
              "disabled:pointer-events-none disabled:opacity-35",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50",
            )}
          >
            <Buy size="small" set="bold" primaryColor="currentColor" />
          </button>

          {/* Expanded — soft qty panel / success on opaque shell */}
          <div
            className={cn(
              "flex h-full w-full items-center bg-[#FAFAF9]",
              "transition-[opacity,transform]",
              contentMotion,
              isExpanded
                ? "relative translate-x-0 opacity-100 delay-75"
                : "pointer-events-none absolute inset-0 translate-x-1.5 opacity-0 delay-0 rtl:-translate-x-1.5",
              reducedMotion && "delay-0",
            )}
            aria-hidden={!isExpanded}
          >
            {isSuccess ? (
              <div
                className="flex w-full items-center justify-center gap-1.5 text-[12px] font-bold text-[#1a7a4c]"
                role="status"
                aria-live="polite"
              >
                <TickSquare
                  size="small"
                  set="bold"
                  primaryColor="currentColor"
                />
                اضافه شد
              </div>
            ) : (
              <SoftQtyConfirm
                qty={qty}
                onChange={setQty}
                onConfirm={confirm}
                variant="card"
                tabbable={isOpen}
              />
            )}
          </div>
        </div>
      </div>
    </>
  );
}
