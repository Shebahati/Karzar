"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronLeft, ChevronRight, Scan } from "react-iconly";
import { ProductPlaceholder } from "@/components/ui/product-placeholder";
import { SafeImage } from "@/components/ui/safe-image";
import { lazyImageProps, lcpImageProps } from "@/lib/cwv";
import { toSafeNextImageSrc } from "@/lib/image-remote-patterns";
import { useFocusTrap } from "@/lib/use-focus-trap";
import { cn } from "@/lib/utils";
import type { ProductImage } from "@/types/product";

type GalleryImage = ProductImage & { url: string };

const SWIPE_THRESHOLD = 48;
const LB_MIN_SCALE = 1;
const LB_MAX_SCALE = 4;
const LB_DOUBLE_TAP_SCALE = 2.5;
const LB_DOUBLE_TAP_MS = 280;
const LB_DESKTOP_SCALE = 2.15;

type LbMobileZoom = { scale: number; x: number; y: number };

function clampLbScale(scale: number) {
  return Math.min(LB_MAX_SCALE, Math.max(LB_MIN_SCALE, scale));
}

function clampLbPan(
  scale: number,
  x: number,
  y: number,
  width: number,
  height: number,
): { x: number; y: number } {
  if (scale <= 1.01) return { x: 0, y: 0 };
  const maxX = ((scale - 1) * width) / 2;
  const maxY = ((scale - 1) * height) / 2;
  return {
    x: Math.min(maxX, Math.max(-maxX, x)),
    y: Math.min(maxY, Math.max(-maxY, y)),
  };
}

function pinchDistance(
  a: { x: number; y: number },
  b: { x: number; y: number },
) {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

export function ProductGallery({
  images,
  alt,
}: {
  images: ProductImage[];
  alt: string;
}) {
  const list = useMemo(
    () =>
      images
        .map((img) => {
          const url = toSafeNextImageSrc(img.url);
          return url ? ({ ...img, url } satisfies GalleryImage) : null;
        })
        .filter((img): img is GalleryImage => img != null),
    [images],
  );

  const primaryId = list.find((i) => i.is_primary)?.id ?? list[0]?.id ?? 0;
  const [activeId, setActiveId] = useState(primaryId);
  const activeIndex = Math.max(
    0,
    list.findIndex((i) => i.id === activeId),
  );
  const current = list[activeIndex] ?? list[0];
  const reducedMotion = useReducedMotion();

  const [lightbox, setLightbox] = useState(false);
  const [zoom, setZoom] = useState(false);
  const [origin, setOrigin] = useState({ x: 50, y: 50 });
  const stageRef = useRef<HTMLDivElement>(null);
  const swipeRef = useRef<{ x: number; y: number; moved: boolean } | null>(
    null,
  );

  const goTo = useCallback(
    (index: number) => {
      if (!list.length) return;
      const next = ((index % list.length) + list.length) % list.length;
      setActiveId(list[next]!.id);
      setZoom(false);
    },
    [list],
  );

  const goPrev = useCallback(() => goTo(activeIndex - 1), [activeIndex, goTo]);
  const goNext = useCallback(() => goTo(activeIndex + 1), [activeIndex, goTo]);

  const openLightbox = useCallback(() => {
    setZoom(false);
    setLightbox(true);
  }, []);

  const closeLightbox = useCallback(() => {
    setLightbox(false);
    setZoom(false);
  }, []);

  useEffect(() => {
    if (!lightbox) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeLightbox();
      else if (e.key === "ArrowRight") goPrev(); // RTL: right → previous
      else if (e.key === "ArrowLeft") goNext();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [lightbox, closeLightbox, goPrev, goNext]);

  const updateOrigin = (clientX: number, clientY: number) => {
    if (!stageRef.current) return;
    const rect = stageRef.current.getBoundingClientRect();
    setOrigin({
      x: Math.min(100, Math.max(0, ((clientX - rect.left) / rect.width) * 100)),
      y: Math.min(100, Math.max(0, ((clientY - rect.top) / rect.height) * 100)),
    });
  };

  /**
   * First-viewport budget: keep the main stage fully visible under sticky header
   * + crumbs. Cap with rem so tall monitors don’t inflate; shrink via svh/dvh
   * on short / low-res screens. Thumbs sit under the stage (extra chrome when multi).
   */
  const multi = list.length > 1;
  const galleryBudget = multi
    ? "min(32rem, calc(100svh - 12.75rem), calc(100dvh - 12.75rem))"
    : "min(32rem, calc(100svh - 9.25rem), calc(100dvh - 9.25rem))";
  const galleryBudgetShort = multi
    ? "min(26rem, calc(100svh - 10.5rem), calc(100dvh - 10.5rem))"
    : "min(26rem, calc(100svh - 7.75rem), calc(100dvh - 7.75rem))";

  if (!list.length || !current) {
    return (
      <div
        className={cn(
          "relative mx-auto w-full min-w-0 max-w-full overflow-hidden bg-[#E9E8E7]",
          /* Mobile: true square, capped under ~½ viewport (no tall void) */
          "max-lg:aspect-square max-lg:max-h-[min(100vw,48svh)] max-lg:rounded-none",
          "lg:aspect-square lg:w-[min(100%,var(--pdp-gallery-budget))] lg:max-h-[var(--pdp-gallery-budget)] lg:rounded-2xl",
          "[@media(max-height:800px)]:[--pdp-gallery-budget:min(26rem,calc(100svh-7.75rem),calc(100dvh-7.75rem))]",
        )}
        style={
          {
            ["--pdp-gallery-budget"]:
              "min(32rem, calc(100svh - 9.25rem), calc(100dvh - 9.25rem))",
          } as CSSProperties
        }
      >
        <ProductPlaceholder name={alt} />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex w-full min-w-0 max-w-full flex-col gap-2.5 sm:gap-3",
        "max-lg:gap-0",
        "[@media(max-height:800px)]:gap-1.5 [@media(max-height:800px)]:max-lg:gap-0",
      )}
      style={
        {
          ["--pdp-gallery-budget"]: galleryBudget,
        } as CSSProperties
      }
    >
      <div
        className={cn(
          "relative mx-auto min-w-0 w-full max-w-full",
          "lg:w-[min(100%,var(--pdp-gallery-budget))]",
          "[@media(max-height:800px)]:[--pdp-gallery-budget:var(--pdp-gallery-budget-short)]",
        )}
        style={
          {
            ["--pdp-gallery-budget-short"]: galleryBudgetShort,
          } as CSSProperties
        }
      >
        <div
          ref={stageRef}
          role="button"
          tabIndex={0}
          aria-label={`${alt} — نمایش گالری تصاویر`}
          className={cn(
            "group relative w-full min-w-0 max-w-full overflow-hidden touch-pan-y",
            /* Mobile square ≤ ~½ viewport — sticky element height stays content-sized */
            "max-lg:aspect-square max-lg:max-h-[min(100vw,48svh)] max-lg:rounded-none",
            "lg:aspect-square lg:max-h-[var(--pdp-gallery-budget)] lg:rounded-2xl",
            "bg-gradient-to-b from-muted/40 to-muted/20 outline-none",
            "max-lg:ring-0 max-lg:shadow-none",
            "lg:ring-1 lg:ring-steel/[0.07] lg:shadow-[0_16px_36px_-26px_rgba(94,95,94,0.38)]",
            "focus-visible:ring-2 focus-visible:ring-[#D02327]/35",
            zoom ? "cursor-zoom-out" : "cursor-zoom-in",
          )}
          onMouseEnter={(e) => {
            if (
              !window.matchMedia("(hover: hover) and (pointer: fine)").matches
            ) {
              return;
            }
            setZoom(true);
            updateOrigin(e.clientX, e.clientY);
          }}
          onMouseMove={(e) => {
            if (
              !window.matchMedia("(hover: hover) and (pointer: fine)").matches
            ) {
              return;
            }
            setZoom(true);
            updateOrigin(e.clientX, e.clientY);
          }}
          onMouseLeave={() => setZoom(false)}
          onClick={(e) => {
            // Desktop click opens lightbox (hover already handles zoom)
            if (
              window.matchMedia("(hover: hover) and (pointer: fine)").matches &&
              !(e.target as HTMLElement).closest("button")
            ) {
              openLightbox();
            }
          }}
          onPointerDown={(e: ReactPointerEvent<HTMLDivElement>) => {
            if (e.pointerType === "mouse") return;
            swipeRef.current = { x: e.clientX, y: e.clientY, moved: false };
          }}
          onPointerMove={(e: ReactPointerEvent<HTMLDivElement>) => {
            const start = swipeRef.current;
            if (!start) return;
            if (
              Math.abs(e.clientX - start.x) > 8 ||
              Math.abs(e.clientY - start.y) > 8
            ) {
              start.moved = true;
            }
          }}
          onPointerUp={(e: ReactPointerEvent<HTMLDivElement>) => {
            const start = swipeRef.current;
            swipeRef.current = null;
            if (!start || e.pointerType === "mouse") return;
            if ((e.target as HTMLElement).closest("button")) return;

            if (start.moved && multi) {
              const dx = e.clientX - start.x;
              const dy = e.clientY - start.y;
              if (
                Math.abs(dx) >= SWIPE_THRESHOLD &&
                Math.abs(dx) > Math.abs(dy)
              ) {
                // RTL: finger right → next
                if (dx > 0) goNext();
                else goPrev();
              }
              return;
            }

            // Tap opens lightbox (zoom lives inside the viewer)
            openLightbox();
          }}
          onPointerCancel={() => {
            swipeRef.current = null;
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              openLightbox();
            } else if (e.key === "ArrowRight" && multi) {
              e.preventDefault();
              goPrev();
            } else if (e.key === "ArrowLeft" && multi) {
              e.preventDefault();
              goNext();
            }
          }}
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={current.id}
              initial={reducedMotion ? false : { opacity: 0.4 }}
              animate={{ opacity: 1 }}
              exit={reducedMotion ? undefined : { opacity: 0.4 }}
              transition={{
                duration: reducedMotion ? 0.01 : 0.28,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="absolute inset-0"
            >
              <div
                className="absolute inset-0"
                style={{
                  transformOrigin: `${origin.x}% ${origin.y}%`,
                  transform: zoom ? "scale(1.9)" : "scale(1)",
                  transition: reducedMotion
                    ? "none"
                    : zoom
                      ? "transform 70ms linear"
                      : "transform 320ms cubic-bezier(0.22, 1, 0.36, 1)",
                }}
              >
                <SafeImage
                  src={current.url}
                  alt={alt}
                  fill
                  sizes="(max-width: 1023px) 100vw, (max-width: 1024px) 50vw, 34vw"
                  className="object-cover object-center select-none"
                  draggable={false}
                  fallback={<ProductPlaceholder name={alt} />}
                  {...lcpImageProps()}
                />
              </div>
            </motion.div>
          </AnimatePresence>

          {multi && (
            <>
              <NavChevron
                side="start"
                label="تصویر قبلی"
                onClick={(e) => {
                  e.stopPropagation();
                  goPrev();
                }}
              >
                <ChevronRight set="light" size="small" />
              </NavChevron>
              <NavChevron
                side="end"
                label="تصویر بعدی"
                onClick={(e) => {
                  e.stopPropagation();
                  goNext();
                }}
              >
                <ChevronLeft set="light" size="small" />
              </NavChevron>
            </>
          )}

          <button
            type="button"
            aria-label="نمایش تمام‌صفحه"
            onClick={(e) => {
              e.stopPropagation();
              openLightbox();
            }}
            className={cn(
              "absolute start-3 bottom-3 z-10 grid h-9 w-9 place-items-center rounded-full",
              /* Clear soft-sheet −mt overlap while sticky */
              "max-lg:bottom-8",
              "bg-white/75 text-steel shadow-soft backdrop-blur-md transition-all duration-300",
              "hover:bg-white hover:text-karzar-500",
              "max-lg:bg-foreground/70 max-lg:text-white max-lg:opacity-100",
              "lg:opacity-0 lg:group-hover:opacity-100",
            )}
          >
            <Scan set="bold" size="small" primaryColor="currentColor" />
          </button>

          {multi && (
            <span
              className={cn(
                "pointer-events-none absolute end-3 bottom-3 z-10 rounded-full px-2.5 py-1 text-[11px] font-bold tabular-nums backdrop-blur-md",
                "max-lg:bottom-8",
                "max-lg:bg-foreground/75 max-lg:text-white",
                "lg:bg-white/75 lg:text-steel",
              )}
            >
              {activeIndex + 1} / {list.length}
            </span>
          )}
        </div>
      </div>

      {multi && (
        <div
          role="tablist"
          aria-label="تصاویر محصول"
          className={cn(
            "justify-center gap-2 h-scroll no-scrollbar px-0.5 py-1.5 sm:gap-2.5",
            /* Mobile: swipe + counter only; thumbs return at lg (desktop) */
            "hidden lg:flex",
          )}
        >
          {list.map((img, i) => {
            const selected = activeId === img.id;
            return (
              <button
                key={img.id}
                type="button"
                role="tab"
                aria-selected={selected}
                aria-label={`تصویر ${i + 1}`}
                onClick={() => {
                  setActiveId(img.id);
                  setZoom(false);
                }}
                className={cn(
                  "relative h-11 w-11 shrink-0 overflow-hidden rounded-lg bg-muted/35 transition-all duration-300 sm:h-12 sm:w-12",
                  "[@media(max-height:800px)]:h-10 [@media(max-height:800px)]:w-10",
                  selected
                    ? "opacity-100 ring-2 ring-karzar-500 ring-offset-2 ring-offset-background"
                    : "opacity-55 hover:opacity-100",
                )}
              >
                <SafeImage
                  src={img.url}
                  alt=""
                  fill
                  sizes="64px"
                  className="object-cover object-center"
                  fallback={null}
                  {...lazyImageProps()}
                />
              </button>
            );
          })}
        </div>
      )}

      {/* Portal to body — sticky/z PDP sheet must not trap the overlay */}
      <GalleryLightbox
        open={lightbox}
        alt={alt}
        list={list}
        activeIndex={activeIndex}
        onClose={closeLightbox}
        onPrev={goPrev}
        onNext={goNext}
        onSelect={(id) => {
          setActiveId(id);
          setZoom(false);
        }}
      />
    </div>
  );
}

function NavChevron({
  side,
  label,
  onClick,
  children,
}: {
  side: "start" | "end";
  label: string;
  onClick: (e: MouseEvent) => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className={cn(
        "absolute top-1/2 z-10 hidden h-9 w-9 -translate-y-1/2 place-items-center rounded-full",
        "bg-white/80 text-steel shadow-soft backdrop-blur-md transition-all duration-300",
        "hover:bg-white hover:text-karzar-500 sm:grid",
        "opacity-0 group-hover:opacity-100",
        side === "start" ? "start-2.5" : "end-2.5",
      )}
    >
      {children}
    </button>
  );
}

function GalleryLightbox({
  open,
  alt,
  list,
  activeIndex,
  onClose,
  onPrev,
  onNext,
  onSelect,
}: {
  open: boolean;
  alt: string;
  list: GalleryImage[];
  activeIndex: number;
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
  onSelect: (id: number) => void;
}) {
  const [mounted, setMounted] = useState(false);
  const current = list[activeIndex]!;
  const multi = list.length > 1;
  const reducedMotion = useReducedMotion();
  const dialogRef = useRef<HTMLDivElement>(null);
  const swipeRef = useRef<{ x: number; y: number; moved: boolean } | null>(
    null,
  );
  /** Desktop fine-pointer click zoom (unchanged UX). */
  const [lbZoom, setLbZoom] = useState(false);
  const [origin, setOrigin] = useState({ x: 50, y: 50 });
  /**
   * Mobile-only image-layer zoom/pan via CSS transform.
   * Never enables document / viewport pinch-zoom.
   */
  const [mobileZoom, setMobileZoom] = useState<LbMobileZoom>({
    scale: 1,
    x: 0,
    y: 0,
  });
  /** Gesture handlers read latest zoom without re-binding; writers update both. */
  const mobileZoomRef = useRef(mobileZoom);
  const frameRef = useRef<HTMLDivElement>(null);
  const pointersRef = useRef(
    new Map<number, { x: number; y: number }>(),
  );
  const pinchRef = useRef<{
    distance: number;
    scale: number;
    x: number;
    y: number;
    midX: number;
    midY: number;
  } | null>(null);
  const panRef = useRef<{
    startX: number;
    startY: number;
    originX: number;
    originY: number;
  } | null>(null);
  const lastTapRef = useRef<{ t: number; x: number; y: number } | null>(null);
  const gestureMovedRef = useRef(false);
  /** True while pinch/pan is live — disables CSS transition on the image layer. */
  const [gestureLive, setGestureLive] = useState(false);
  /** Keep translate+scale path mounted through zoom-out so CSS can interpolate. */
  const [mobileLayer, setMobileLayer] = useState(false);
  const mobileLayerTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  const clearMobileLayerTimer = useCallback(() => {
    if (mobileLayerTimerRef.current != null) {
      clearTimeout(mobileLayerTimerRef.current);
      mobileLayerTimerRef.current = null;
    }
  }, []);

  const resetMobileZoom = useCallback(() => {
    const next = { scale: 1, x: 0, y: 0 };
    mobileZoomRef.current = next;
    setMobileZoom(next);
    pinchRef.current = null;
    panRef.current = null;
    pointersRef.current.clear();
    lastTapRef.current = null;
    setGestureLive(false);
    clearMobileLayerTimer();
    setMobileLayer(false);
  }, [clearMobileLayerTimer]);

  useEffect(() => setMounted(true), []);

  useEffect(
    () => () => {
      clearMobileLayerTimer();
    },
    [clearMobileLayerTimer],
  );

  useFocusTrap(dialogRef, open, onClose);

  useEffect(() => {
    if (!open) {
      setLbZoom(false);
      resetMobileZoom();
    }
  }, [open, resetMobileZoom]);

  useEffect(() => {
    setLbZoom(false);
    resetMobileZoom();
  }, [activeIndex, resetMobileZoom]);

  const applyMobileZoom = useCallback(
    (next: LbMobileZoom) => {
      const frame = frameRef.current;
      const w = frame?.clientWidth ?? 1;
      const h = frame?.clientHeight ?? 1;
      const scale = clampLbScale(next.scale);
      const pan =
        scale <= 1.01
          ? { x: 0, y: 0 }
          : clampLbPan(scale, next.x, next.y, w, h);
      const clamped = { scale: scale <= 1.01 ? 1 : scale, x: pan.x, y: pan.y };
      mobileZoomRef.current = clamped;
      setMobileZoom(clamped);
      setLbZoom(false);
      clearMobileLayerTimer();
      if (clamped.scale > 1) {
        setMobileLayer(true);
      } else {
        setMobileLayer(true);
        mobileLayerTimerRef.current = setTimeout(() => {
          setMobileLayer(false);
          mobileLayerTimerRef.current = null;
        }, 300);
      }
    },
    [clearMobileLayerTimer],
  );

  const handlePrev = () => {
    setLbZoom(false);
    resetMobileZoom();
    onPrev();
  };
  const handleNext = () => {
    setLbZoom(false);
    resetMobileZoom();
    onNext();
  };
  const handleSelect = (id: number) => {
    setLbZoom(false);
    resetMobileZoom();
    onSelect(id);
  };

  const updateOrigin = (clientX: number, clientY: number) => {
    if (!frameRef.current) return;
    const rect = frameRef.current.getBoundingClientRect();
    setOrigin({
      x: Math.min(100, Math.max(0, ((clientX - rect.left) / rect.width) * 100)),
      y: Math.min(100, Math.max(0, ((clientY - rect.top) / rect.height) * 100)),
    });
  };

  const isFinePointer = () =>
    typeof window !== "undefined" &&
    window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  const onFramePointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.pointerType === "mouse" && isFinePointer()) {
      swipeRef.current = { x: e.clientX, y: e.clientY, moved: false };
      return;
    }

    // Touch / pen — image-layer gestures only
    e.currentTarget.setPointerCapture(e.pointerId);
    pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    gestureMovedRef.current = false;
    swipeRef.current = { x: e.clientX, y: e.clientY, moved: false };

    if (pointersRef.current.size === 2) {
      const pts = [...pointersRef.current.values()];
      const a = pts[0]!;
      const b = pts[1]!;
      const z = mobileZoomRef.current;
      pinchRef.current = {
        distance: Math.max(1, pinchDistance(a, b)),
        scale: z.scale,
        x: z.x,
        y: z.y,
        midX: (a.x + b.x) / 2,
        midY: (a.y + b.y) / 2,
      };
      panRef.current = null;
      setGestureLive(true);
      setLbZoom(false);
      return;
    }

    if (mobileZoomRef.current.scale > 1.01) {
      panRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        originX: mobileZoomRef.current.x,
        originY: mobileZoomRef.current.y,
      };
      setGestureLive(true);
    }
  };

  const onFramePointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.pointerType === "mouse" && isFinePointer()) {
      const start = swipeRef.current;
      if (!start) return;
      if (
        Math.abs(e.clientX - start.x) > 8 ||
        Math.abs(e.clientY - start.y) > 8
      ) {
        start.moved = true;
      }
      return;
    }

    if (!pointersRef.current.has(e.pointerId)) return;
    pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });

    const start = swipeRef.current;
    if (
      start &&
      (Math.abs(e.clientX - start.x) > 8 || Math.abs(e.clientY - start.y) > 8)
    ) {
      start.moved = true;
      gestureMovedRef.current = true;
    }

    if (pointersRef.current.size >= 2 && pinchRef.current) {
      const pts = [...pointersRef.current.values()];
      const a = pts[0]!;
      const b = pts[1]!;
      const dist = Math.max(1, pinchDistance(a, b));
      const pinch = pinchRef.current;
      const nextScale = clampLbScale(pinch.scale * (dist / pinch.distance));
      const midX = (a.x + b.x) / 2;
      const midY = (a.y + b.y) / 2;
      const frame = frameRef.current;
      if (!frame) return;
      const rect = frame.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      // Anchor under pinch midpoint + follow mid-point drift
      const nextX =
        pinch.x +
        (midX - pinch.midX) +
        (pinch.midX - cx) * (1 - nextScale / Math.max(pinch.scale, 0.001));
      const nextY =
        pinch.y +
        (midY - pinch.midY) +
        (pinch.midY - cy) * (1 - nextScale / Math.max(pinch.scale, 0.001));
      applyMobileZoom({ scale: nextScale, x: nextX, y: nextY });
      return;
    }

    if (panRef.current && mobileZoomRef.current.scale > 1.01) {
      const pan = panRef.current;
      applyMobileZoom({
        scale: mobileZoomRef.current.scale,
        x: pan.originX + (e.clientX - pan.startX),
        y: pan.originY + (e.clientY - pan.startY),
      });
    }
  };

  const endTouchPointer = (e: ReactPointerEvent<HTMLDivElement>) => {
    pointersRef.current.delete(e.pointerId);
    if (pointersRef.current.size < 2) {
      pinchRef.current = null;
      // Snap near-min back to rest
      const z = mobileZoomRef.current;
      if (z.scale < 1.05) {
        applyMobileZoom({ scale: 1, x: 0, y: 0 });
      } else {
        applyMobileZoom(z);
      }
    }
    if (pointersRef.current.size === 0) {
      panRef.current = null;
      setGestureLive(false);
    } else if (
      pointersRef.current.size === 1 &&
      mobileZoomRef.current.scale > 1.01
    ) {
      const remaining = [...pointersRef.current.values()][0]!;
      panRef.current = {
        startX: remaining.x,
        startY: remaining.y,
        originX: mobileZoomRef.current.x,
        originY: mobileZoomRef.current.y,
      };
      setGestureLive(true);
    }
  };

  const onFramePointerUp = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.pointerType === "mouse" && isFinePointer()) {
      const start = swipeRef.current;
      swipeRef.current = null;
      if (!start) return;

      if (start.moved && multi) {
        const dx = e.clientX - start.x;
        const dy = e.clientY - start.y;
        if (
          Math.abs(dx) >= SWIPE_THRESHOLD &&
          Math.abs(dx) > Math.abs(dy)
        ) {
          if (dx > 0) handleNext();
          else handlePrev();
        }
        return;
      }

      updateOrigin(e.clientX, e.clientY);
      clearMobileLayerTimer();
      setMobileLayer(false);
      mobileZoomRef.current = { scale: 1, x: 0, y: 0 };
      setMobileZoom({ scale: 1, x: 0, y: 0 });
      setLbZoom((z) => !z);
      return;
    }

    const start = swipeRef.current;
    const wasPinching =
      pinchRef.current != null || pointersRef.current.size > 1;
    const moved = start?.moved || gestureMovedRef.current;
    endTouchPointer(e);
    swipeRef.current = null;

    if (wasPinching) return;
    if (pointersRef.current.size > 0) return;

    // Swipe between images only when not zoomed
    if (moved && multi && mobileZoomRef.current.scale <= 1.01) {
      if (!start) return;
      const dx = e.clientX - start.x;
      const dy = e.clientY - start.y;
      if (Math.abs(dx) >= SWIPE_THRESHOLD && Math.abs(dx) > Math.abs(dy)) {
        if (dx > 0) handleNext();
        else handlePrev();
      }
      lastTapRef.current = null;
      return;
    }

    if (moved) return;

    // Double-tap zoom in/out (touch only)
    const now = Date.now();
    const prev = lastTapRef.current;
    if (
      prev &&
      now - prev.t <= LB_DOUBLE_TAP_MS &&
      Math.hypot(e.clientX - prev.x, e.clientY - prev.y) < 36
    ) {
      lastTapRef.current = null;
      const frame = frameRef.current;
      if (!frame) return;
      const rect = frame.getBoundingClientRect();
      const z = mobileZoomRef.current;
      if (z.scale > 1.05) {
        applyMobileZoom({ scale: 1, x: 0, y: 0 });
        setLbZoom(false);
        return;
      }
      const target = LB_DOUBLE_TAP_SCALE;
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const nextX = (cx - e.clientX) * (target - 1);
      const nextY = (cy - e.clientY) * (target - 1);
      applyMobileZoom({ scale: target, x: nextX, y: nextY });
      setLbZoom(false);
      return;
    }

    lastTapRef.current = { t: now, x: e.clientX, y: e.clientY };
  };

  const onFramePointerCancel = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.pointerType === "mouse" && isFinePointer()) {
      swipeRef.current = null;
      return;
    }
    endTouchPointer(e);
    swipeRef.current = null;
  };

  const fadeMs = reducedMotion ? 0.01 : 0.22;
  const crossfadeMs = reducedMotion ? 0.01 : 0.26;
  const mobileZoomed = mobileZoom.scale > 1.01;
  const useMobileTransform = mobileLayer || mobileZoomed || gestureLive;
  const imageTransform: CSSProperties = useMobileTransform
    ? {
        transformOrigin: "center center",
        transform: `translate3d(${mobileZoom.x}px, ${mobileZoom.y}px, 0) scale(${mobileZoom.scale})`,
        transition:
          gestureLive || reducedMotion
            ? "none"
            : "transform 280ms cubic-bezier(0.22, 1, 0.36, 1)",
      }
    : {
        transformOrigin: `${origin.x}% ${origin.y}%`,
        transform: lbZoom ? `scale(${LB_DESKTOP_SCALE})` : "scale(1)",
        transition: reducedMotion
          ? "none"
          : lbZoom
            ? "transform 70ms linear"
            : "transform 320ms cubic-bezier(0.22, 1, 0.36, 1)",
      };

  if (!mounted) return null;

  return createPortal(
    <AnimatePresence>
      {open ? (
        <motion.div
          key="pdp-gallery-lightbox"
          ref={dialogRef}
          role="dialog"
          aria-modal="true"
          aria-label={`گالری تصاویر — ${alt}`}
          className="fixed inset-0 z-[100] flex flex-col"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: fadeMs }}
        >
          {/* Dim page — above header/nav via portal + z-[100] */}
          <button
            type="button"
            aria-label="بستن"
            className="absolute inset-0 bg-[#0e0f0f]/86 backdrop-blur-[2px]"
            onClick={onClose}
          />

          {/* dir=ltr: close stays physical top-right under site-wide RTL */}
          <div
            dir="ltr"
            className="relative z-10 flex shrink-0 items-center justify-between gap-3 px-4 pb-2 pt-[max(0.75rem,env(safe-area-inset-top))]"
            onClick={(e) => {
              if (e.target === e.currentTarget) onClose();
            }}
          >
            <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-steel shadow-soft tabular-nums">
              {activeIndex + 1} / {list.length}
            </span>
            <button
              type="button"
              aria-label="بستن گالری"
              onClick={onClose}
              className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-white bg-white p-0 text-[#0e0f0f] shadow-[0_4px_20px_rgba(0,0,0,0.35)] ring-2 ring-black/25 transition hover:bg-white hover:text-karzar-500"
            >
              <svg
                aria-hidden
                viewBox="0 0 24 24"
                width={22}
                height={22}
                fill="none"
                stroke="currentColor"
                strokeWidth={2.25}
                strokeLinecap="round"
                className="block shrink-0"
              >
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
          </div>

          <div
            className="relative z-10 flex min-h-0 flex-1 flex-col items-center justify-center gap-3 px-3 pb-2 sm:gap-4 sm:px-8"
            onClick={(e) => {
              if (e.target === e.currentTarget) onClose();
            }}
          >
            <div
              className="relative flex min-h-0 w-full flex-1 items-center justify-center"
              onClick={(e) => {
                if (e.target === e.currentTarget) onClose();
              }}
            >
              {multi && !mobileZoomed && (
                <>
                  <button
                    type="button"
                    aria-label="تصویر قبلی"
                    onClick={handlePrev}
                    className="absolute start-1 top-1/2 z-20 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-white text-steel shadow-card transition hover:text-karzar-500 sm:start-4"
                  >
                    <ChevronRight set="light" />
                  </button>
                  <button
                    type="button"
                    aria-label="تصویر بعدی"
                    onClick={handleNext}
                    className="absolute end-1 top-1/2 z-20 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-white text-steel shadow-card transition hover:text-karzar-500 sm:end-4"
                  >
                    <ChevronLeft set="light" />
                  </button>
                </>
              )}

              <div
                ref={frameRef}
                className={cn(
                  /* Mobile: keep prior flex fill; desktop: width = height budget so aspect-square stays square (w-full+max-h alone yields a wide rect + object-cover crop). */
                  "relative mx-auto aspect-square h-auto w-full max-h-[min(68dvh,760px)] max-w-4xl overflow-hidden rounded-2xl",
                  "lg:w-[min(100%,min(68dvh,760px))] lg:max-w-[min(100%,min(68dvh,760px))]",
                  /* touch-none: contain pinch/pan to this layer; no page zoom */
                  "touch-none select-none",
                  "bg-white shadow-[0_24px_64px_-20px_rgba(0,0,0,0.45)] ring-1 ring-white/80",
                  lbZoom || mobileZoomed ? "cursor-zoom-out" : "cursor-zoom-in",
                )}
                onMouseMove={(e) => {
                  if (!lbZoom || mobileZoomed) return;
                  if (!isFinePointer()) return;
                  updateOrigin(e.clientX, e.clientY);
                }}
                onPointerDown={onFramePointerDown}
                onPointerMove={onFramePointerMove}
                onPointerUp={onFramePointerUp}
                onPointerCancel={onFramePointerCancel}
              >
                <AnimatePresence mode="wait" initial={false}>
                  <motion.div
                    key={current.id}
                    initial={reducedMotion ? false : { opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={reducedMotion ? undefined : { opacity: 0 }}
                    transition={{
                      duration: crossfadeMs,
                      ease: [0.22, 1, 0.36, 1],
                    }}
                    className="absolute inset-0"
                  >
                    <div className="absolute inset-0" style={imageTransform}>
                      <SafeImage
                        src={current.url}
                        alt={alt}
                        fill
                        sizes="100vw"
                        className="pointer-events-none object-cover object-center select-none"
                        draggable={false}
                        fallback={<ProductPlaceholder name={alt} />}
                        {...lazyImageProps()}
                      />
                    </div>
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>

            {multi ? (
              <div className="flex shrink-0 justify-center gap-2 h-scroll no-scrollbar px-1 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-0.5">
                {list.map((img, i) => {
                  const selected = i === activeIndex;
                  return (
                    <button
                      key={img.id}
                      type="button"
                      aria-label={`تصویر ${i + 1}`}
                      aria-current={selected || undefined}
                      onClick={() => handleSelect(img.id)}
                      className={cn(
                        "relative h-14 w-14 shrink-0 overflow-hidden rounded-xl bg-white shadow-soft transition-all duration-300 sm:h-16 sm:w-16",
                        selected
                          ? "opacity-100 ring-2 ring-karzar-500 ring-offset-2 ring-offset-transparent"
                          : "opacity-55 hover:opacity-95",
                      )}
                    >
                      <SafeImage
                        src={img.url}
                        alt=""
                        fill
                        sizes="64px"
                        className="object-cover object-center"
                        fallback={null}
                        {...lazyImageProps()}
                      />
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="pb-[max(0.75rem,env(safe-area-inset-bottom))]" />
            )}
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}
