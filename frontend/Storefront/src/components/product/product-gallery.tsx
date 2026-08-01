"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, ChevronRight, CloseSquare, Scan } from "react-iconly";
import { ProductPlaceholder } from "@/components/ui/product-placeholder";
import { SafeImage } from "@/components/ui/safe-image";
import { lazyImageProps, lcpImageProps } from "@/lib/cwv";
import { toSafeNextImageSrc } from "@/lib/image-remote-patterns";
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

  if (!list.length || !current) {
    return (
      <div className="relative aspect-square overflow-hidden rounded-xl bg-[#E9E8E7]">
        <ProductPlaceholder name={alt} />
      </div>
    );
  }

  const multi = list.length > 1;

  return (
    <div className="flex flex-col-reverse gap-3 sm:flex-row sm:gap-4">
      {multi && (
        <div
          role="tablist"
          aria-label="تصاویر محصول"
          className="flex gap-2.5 overflow-x-auto pb-0.5 no-scrollbar sm:flex-col sm:overflow-visible"
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
                  "relative h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-muted/35 transition-all duration-300 sm:h-16 sm:w-16",
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

      <div className="relative min-w-0 flex-1">
        <div
          ref={stageRef}
          role="button"
          tabIndex={0}
          aria-label={`${alt} — بزرگ‌نمایی یا نمایش تمام‌صفحه`}
          className={cn(
            "group relative aspect-square overflow-hidden rounded-xl bg-muted/35 outline-none",
            "focus-visible:ring-2 focus-visible:ring-karzar-500/40",
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

            // Tap to toggle zoom on touch
            if (!zoom) {
              updateOrigin(e.clientX, e.clientY);
              setZoom(true);
            } else {
              setZoom(false);
            }
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
              initial={{ opacity: 0.4 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0.4 }}
              transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-0"
            >
              <div
                className="absolute inset-0 will-change-transform"
                style={{
                  transformOrigin: `${origin.x}% ${origin.y}%`,
                  transform: zoom ? "scale(1.9)" : "scale(1)",
                  transition: zoom
                    ? "transform 70ms linear"
                    : "transform 320ms cubic-bezier(0.22, 1, 0.36, 1)",
                }}
              >
                <SafeImage
                  src={current.url}
                  alt={alt}
                  fill
                  sizes="(max-width: 768px) 100vw, 50vw"
                  className="object-contain p-4 select-none"
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
              "absolute bottom-3 start-3 z-10 grid h-9 w-9 place-items-center rounded-full",
              "bg-white/75 text-steel shadow-soft backdrop-blur-md transition-all duration-300",
              "hover:bg-white hover:text-karzar-500",
              "opacity-90 sm:opacity-0 sm:group-hover:opacity-100",
            )}
          >
            <Scan set="bold" size="small" primaryColor="currentColor" />
          </button>

          {multi && (
            <span className="pointer-events-none absolute bottom-3 end-3 z-10 rounded-full bg-white/75 px-2.5 py-1 text-[11px] font-bold tabular-nums text-steel backdrop-blur-md">
              {activeIndex + 1} / {list.length}
            </span>
          )}
        </div>
      </div>

      <AnimatePresence>
        {lightbox ? (
          <GalleryLightbox
            key="pdp-lightbox"
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
        ) : null}
      </AnimatePresence>
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
  alt,
  list,
  activeIndex,
  onClose,
  onPrev,
  onNext,
  onSelect,
}: {
  alt: string;
  list: GalleryImage[];
  activeIndex: number;
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
  onSelect: (id: number) => void;
}) {
  const current = list[activeIndex]!;
  const multi = list.length > 1;
  const swipeRef = useRef<{ x: number; y: number; moved: boolean } | null>(
    null,
  );
  const [lbZoom, setLbZoom] = useState(false);
  const [origin, setOrigin] = useState({ x: 50, y: 50 });
  const frameRef = useRef<HTMLDivElement>(null);

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

  return (
    <motion.div
      role="dialog"
      aria-modal="true"
      aria-label={`گالری تصاویر — ${alt}`}
      className="fixed inset-0 z-[80] flex flex-col"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.22 }}
    >
      <button
        type="button"
        aria-label="بستن"
        className="absolute inset-0 bg-steel/45 backdrop-blur-xl supports-[backdrop-filter]:bg-steel/30"
        onClick={onClose}
      />

      <div className="relative z-10 flex items-center justify-between gap-3 px-4 pb-2 pt-[max(0.75rem,env(safe-area-inset-top))]">
        <span className="rounded-full bg-white/70 px-3 py-1.5 text-xs font-bold text-steel backdrop-blur-md">
          {activeIndex + 1} / {list.length}
        </span>
        <button
          type="button"
          aria-label="بستن گالری"
          onClick={onClose}
          className="grid h-10 w-10 place-items-center rounded-full bg-white/75 text-steel shadow-soft backdrop-blur-md transition hover:bg-white hover:text-karzar-500"
        >
          <CloseSquare set="bold" size="small" primaryColor="currentColor" />
        </button>
      </div>

      <div className="relative z-10 flex min-h-0 flex-1 items-center justify-center px-3 pb-3 sm:px-8">
        {multi && (
          <>
            <button
              type="button"
              aria-label="تصویر قبلی"
              onClick={handlePrev}
              className="absolute start-2 top-1/2 z-20 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-white/75 text-steel shadow-card backdrop-blur-md transition hover:bg-white hover:text-karzar-500 sm:start-6"
            >
              <ChevronRight set="light" />
            </button>
            <button
              type="button"
              aria-label="تصویر بعدی"
              onClick={handleNext}
              className="absolute end-2 top-1/2 z-20 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-white/75 text-steel shadow-card backdrop-blur-md transition hover:bg-white hover:text-karzar-500 sm:end-6"
            >
              <ChevronLeft set="light" />
            </button>
          </>
        )}

        <div
          ref={frameRef}
          className={cn(
            "relative mx-auto aspect-square h-auto w-full max-h-[min(78dvh,820px)] max-w-5xl overflow-hidden rounded-2xl",
            "bg-white/55 shadow-floating ring-1 ring-white/50 backdrop-blur-2xl",
            "supports-[backdrop-filter]:bg-white/40",
            lbZoom ? "cursor-zoom-out" : "cursor-zoom-in",
          )}
          onMouseMove={(e) => {
            if (!lbZoom) return;
            updateOrigin(e.clientX, e.clientY);
          }}
          onPointerDown={(e) => {
            swipeRef.current = { x: e.clientX, y: e.clientY, moved: false };
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
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-0"
            >
              <div
                className="absolute inset-0 will-change-transform"
                style={{
                  transformOrigin: `${origin.x}% ${origin.y}%`,
                  transform: lbZoom ? "scale(2.15)" : "scale(1)",
                  transition: lbZoom
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

      {multi && (
        <div className="relative z-10 flex justify-center gap-2 overflow-x-auto px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-1 no-scrollbar">
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
                  "relative h-12 w-12 shrink-0 overflow-hidden rounded-lg bg-white/50 backdrop-blur-md transition-all duration-300",
                  selected
                    ? "opacity-100 ring-2 ring-karzar-500 ring-offset-2 ring-offset-transparent"
                    : "opacity-50 hover:opacity-90",
                )}
              >
                <SafeImage
                  src={img.url}
                  alt=""
                  fill
                  sizes="48px"
                  className="object-contain p-0.5"
                  fallback={null}
                  {...lazyImageProps()}
                />
              </button>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
