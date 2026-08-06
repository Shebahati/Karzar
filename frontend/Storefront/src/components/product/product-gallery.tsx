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
                  className="object-contain p-6 select-none lg:p-4"
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
                  className="object-contain p-1"
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
  const [lbZoom, setLbZoom] = useState(false);
  const [origin, setOrigin] = useState({ x: 50, y: 50 });
  const frameRef = useRef<HTMLDivElement>(null);

  useEffect(() => setMounted(true), []);

  useFocusTrap(dialogRef, open, onClose);

  useEffect(() => {
    if (!open) setLbZoom(false);
  }, [open]);

  const handlePrev = () => {
    setLbZoom(false);
    onPrev();
  };
  const handleNext = () => {
    setLbZoom(false);
    onNext();
  };
  const handleSelect = (id: number) => {
    setLbZoom(false);
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

  const fadeMs = reducedMotion ? 0.01 : 0.22;
  const crossfadeMs = reducedMotion ? 0.01 : 0.26;

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
            className="absolute inset-0 bg-[#0e0f0f]/72 backdrop-blur-[2px]"
            onClick={onClose}
          />

          <div className="relative z-10 flex shrink-0 items-center justify-between gap-3 px-4 pb-2 pt-[max(0.75rem,env(safe-area-inset-top))]">
            <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-steel shadow-soft">
              {activeIndex + 1} / {list.length}
            </span>
            <button
              type="button"
              aria-label="بستن گالری"
              onClick={onClose}
              className="grid h-11 w-11 place-items-center rounded-full bg-white text-[1.65rem] leading-none text-steel shadow-card transition hover:bg-white hover:text-karzar-500"
            >
              <span aria-hidden className="translate-y-[-1px]">
                ×
              </span>
            </button>
          </div>

          <div className="relative z-10 flex min-h-0 flex-1 flex-col items-center justify-center gap-3 px-3 pb-2 sm:gap-4 sm:px-8">
            <div className="relative flex min-h-0 w-full flex-1 items-center justify-center">
              {multi && (
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
                  "relative mx-auto aspect-square h-auto w-full max-h-[min(68dvh,760px)] max-w-4xl overflow-hidden rounded-2xl touch-manipulation",
                  "bg-white shadow-[0_24px_64px_-20px_rgba(0,0,0,0.45)] ring-1 ring-white/80",
                  lbZoom ? "cursor-zoom-out" : "cursor-zoom-in",
                )}
                onMouseMove={(e) => {
                  if (!lbZoom) return;
                  updateOrigin(e.clientX, e.clientY);
                }}
                onPointerDown={(e) => {
                  swipeRef.current = {
                    x: e.clientX,
                    y: e.clientY,
                    moved: false,
                  };
                }}
                onPointerMove={(e) => {
                  const start = swipeRef.current;
                  if (!start) return;
                  if (
                    Math.abs(e.clientX - start.x) > 8 ||
                    Math.abs(e.clientY - start.y) > 8
                  ) {
                    start.moved = true;
                  }
                }}
                onPointerUp={(e) => {
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
                  setLbZoom((z) => !z);
                }}
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
                    <div
                      className="absolute inset-0"
                      style={{
                        transformOrigin: `${origin.x}% ${origin.y}%`,
                        transform: lbZoom ? "scale(2.15)" : "scale(1)",
                        transition: reducedMotion
                          ? "none"
                          : lbZoom
                            ? "transform 70ms linear"
                            : "transform 320ms cubic-bezier(0.22, 1, 0.36, 1)",
                      }}
                    >
                      <SafeImage
                        src={current.url}
                        alt={alt}
                        fill
                        sizes="100vw"
                        className="object-contain p-4 sm:p-8 select-none"
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
                        className="object-contain p-1"
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
