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
import { cn, formatNumber } from "@/lib/utils";
import { useCartStore } from "@/store/cart-store";
import type { ProductSummary } from "@/types/product";

/** Incomplete expand → add 1 unit after this delay (or sooner on dismiss). */
export const CARD_ADD_FALLBACK_MS = 4000;
const SUCCESS_MS = 1100;
const MAX_QTY = 99;

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
 * Product-card-only add-to-cart CTA:
 * expand → qty stepper → confirm tick.
 * If the user abandons without confirming, adds 1 unit once.
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
  const reducedMotion = usePrefersReducedMotion();
  const rootRef = useRef<HTMLDivElement>(null);
  const committedRef = useRef(false);
  const phaseRef = useRef<Phase>("idle");
  const fallbackTimerRef = useRef<number | null>(null);
  const successTimerRef = useRef<number | null>(null);
  const dismissImplRef = useRef<DismissFn>(() => {});
  /** Stable identity for single-active expander registry. */
  const dismissStable = useCallback(() => {
    dismissImplRef.current();
  }, []);
  const [phase, setPhase] = useState<Phase>("idle");
  const [qty, setQty] = useState(1);
  const labelId = useId();

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
      const n = Math.max(1, Math.min(MAX_QTY, amount));
      addToCart(product, n);
      onAdded?.(n);
      finishSuccess();
    },
    [addToCart, finishSuccess, onAdded, product],
  );

  const dismissWithoutConfirm = useCallback(() => {
    if (phaseRef.current !== "open") return;
    // Fallback: one unit if the user never pressed confirm.
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
    }, CARD_ADD_FALLBACK_MS);
  }, [clearTimers, disabled, dismissStable]);

  const confirm = useCallback(() => {
    if (phaseRef.current !== "open") return;
    commit(qty);
  }, [commit, qty]);

  // Pointer outside / Escape while open
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

  // Scroll / carousel away
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

  // Route change while open
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
      // Unmount mid-expand (navigate away): still add 1 if not confirmed.
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

  const motionClass = reducedMotion
    ? "duration-150"
    : "duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]";

  if (phase === "idle") {
    return (
      <div ref={rootRef} className={cn("shrink-0", className)}>
        <button
          type="button"
          onClick={(e) => {
            stop(e);
            open();
          }}
          disabled={disabled}
          aria-label="افزودن به سبد خرید"
          aria-expanded={false}
          className={cn(
            "grid h-9 w-9 place-items-center rounded-lg bg-[#D02327] text-white",
            "transition-[transform,background-color,box-shadow]",
            motionClass,
            "hover:bg-[#b81e23] hover:shadow-[0_8px_18px_-10px_rgba(208,35,39,0.55)]",
            "active:scale-95 disabled:pointer-events-none disabled:opacity-35",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/40",
          )}
        >
          <Buy size="small" set="bold" primaryColor="currentColor" />
        </button>
      </div>
    );
  }

  return (
    <div
      ref={rootRef}
      role="group"
      aria-labelledby={labelId}
      className={cn(
        "absolute inset-0 z-10 flex min-h-9 items-center gap-0.5 rounded-xl",
        "bg-[#F7F6F5] px-0.5 shadow-[0_8px_22px_-14px_rgba(94,95,94,0.45)]",
        "ring-1 ring-[#5E5F5E]/10 md:bg-[#F7F6F5]/95 md:backdrop-blur-[6px]",
        "transition-[opacity,transform]",
        motionClass,
        className,
      )}
      onClick={stop}
      onKeyDown={(e) => e.stopPropagation()}
      aria-expanded={phase === "open"}
    >
      <span id={labelId} className="sr-only">
        انتخاب تعداد و تأیید افزودن به سبد
      </span>

      {phase === "success" ? (
        <div
          className="flex w-full items-center justify-center gap-1.5 text-[12px] font-bold text-[#1a7a4c]"
          role="status"
          aria-live="polite"
        >
          <TickSquare size="small" set="bold" primaryColor="currentColor" />
          اضافه شد
        </div>
      ) : (
        <>
          <button
            type="button"
            aria-label="کاهش تعداد"
            onClick={(e) => {
              stop(e);
              setQty((q) => Math.max(1, q - 1));
            }}
            className={cn(
              "grid h-8 w-8 shrink-0 place-items-center rounded-lg text-[15px] font-medium text-[#5E5F5E]",
              "transition-colors hover:bg-white hover:text-[#D02327]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/35",
            )}
          >
            −
          </button>

          <span
            className="min-w-[1.75rem] select-none text-center text-[13px] font-bold tabular-nums text-[#1a1a1a] tnum"
            aria-live="polite"
            aria-atomic="true"
          >
            {formatNumber(qty)}
          </span>

          <button
            type="button"
            aria-label="افزایش تعداد"
            onClick={(e) => {
              stop(e);
              setQty((q) => Math.min(MAX_QTY, q + 1));
            }}
            className={cn(
              "grid h-8 w-8 shrink-0 place-items-center rounded-lg text-[16px] font-medium text-[#5E5F5E]",
              "transition-colors hover:bg-white hover:text-[#D02327]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/35",
            )}
          >
            +
          </button>

          <button
            type="button"
            aria-label="تأیید و افزودن به سبد خرید"
            onClick={(e) => {
              stop(e);
              confirm();
            }}
            className={cn(
              "ms-auto me-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg",
              "bg-[#D02327] text-white shadow-[0_6px_14px_-8px_rgba(208,35,39,0.65)]",
              "transition-[transform,background-color]",
              motionClass,
              "hover:bg-[#b81e23] active:scale-95",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/45",
            )}
          >
            <TickSquare size="small" set="bold" primaryColor="currentColor" />
          </button>
        </>
      )}
    </div>
  );
}
