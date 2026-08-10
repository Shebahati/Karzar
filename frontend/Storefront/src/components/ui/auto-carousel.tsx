"use client";

import {
  Children,
  useCallback,
  useEffect,
  useRef,
  useState,
  type DragEvent as ReactDragEvent,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { ChevronLeft, ChevronRight } from "react-iconly";
import {
  horizontalStepDelta,
  readHorizontalScrollEdges,
  scrollTrackToStart,
} from "@/lib/scroll-edges";
import { cn } from "@/lib/utils";
import { useIsMobileMd, useMotionSafe } from "@/lib/use-motion-safe";

const DRAG_THRESHOLD = 6;

/**
 * Horizontal carousel with chevrons and drag-to-slide.
 * Autoplay is off by default (home/product strips stay manual-only).
 * When opted in: user interaction / hover / offscreen / reduced-motion pause it.
 * Click-through after a drag is suppressed so card links stay intentional.
 *
 * Drag notes:
 * - Do NOT put Tailwind `scroll-smooth` on the track — CSS smooth scrolling
 *   fights per-frame `scrollLeft` writes and makes mouse-drag feel dead.
 * - Snap is disabled while actively dragging for the same reason.
 * - Touch uses native overflow pan; mouse/pen use pointer drag.
 *
 * RTL: chevrons bind to physical left/right. scrollBy({ left }) is not
 * negated — decreasing scrollLeft moves visually left in Chromium/Firefox/WebKit.
 */
export function AutoCarousel({
  children,
  className,
  itemClassName,
  trackClassName,
  autoPlay = false,
  intervalMs = 3200,
  gapClass = "gap-3 sm:gap-4",
  showControls = true,
  controls = "both",
  controlClassName,
}: {
  children: ReactNode;
  className?: string;
  itemClassName?: string;
  trackClassName?: string;
  autoPlay?: boolean;
  intervalMs?: number;
  gapClass?: string;
  showControls?: boolean;
  /** Which chevrons to render: both, physical-right start, or physical-left end. */
  controls?: "both" | "start" | "end";
  /** Extra classes for chevron buttons (position tweaks). */
  controlClassName?: string;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const motionSafe = useMotionSafe();
  const isMobile = useIsMobileMd();
  const [paused, setPaused] = useState(false);
  const [hoverPaused, setHoverPaused] = useState(false);
  const [offscreenPaused, setOffscreenPaused] = useState(false);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [hasOverflow, setHasOverflow] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const resumeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const edgeRaf = useRef<number | null>(null);
  const items = Children.toArray(children);

  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startScroll: number;
    moved: boolean;
    dragging: boolean;
  } | null>(null);
  const suppressClickRef = useRef(false);

  const pauseTemporarily = useCallback(() => {
    setPaused(true);
    if (resumeTimer.current) clearTimeout(resumeTimer.current);
    resumeTimer.current = setTimeout(() => setPaused(false), 5000);
  }, []);

  const updateEdges = useCallback(() => {
    const el = trackRef.current;
    if (!el) return;
    const edges = readHorizontalScrollEdges(el);
    setCanScrollLeft(edges.canScrollLeft);
    setCanScrollRight(edges.canScrollRight);
    setHasOverflow(edges.hasOverflow);
  }, []);

  /** Coalesce scroll/resize edge reads to one layout pass per frame. */
  const scheduleEdges = useCallback(() => {
    if (edgeRaf.current != null) return;
    edgeRaf.current = requestAnimationFrame(() => {
      edgeRaf.current = null;
      updateEdges();
    });
  }, [updateEdges]);

  /** dir: +1 = physical right, -1 = physical left */
  const step = useCallback(
    (dir: 1 | -1) => {
      const el = trackRef.current;
      if (!el) return;
      el.scrollBy({ left: horizontalStepDelta(el, dir), behavior: "smooth" });
      pauseTemporarily();
      // Smooth scroll fires `scroll` / `scrollend`; nudge edges for engines without scrollend.
      requestAnimationFrame(() => {
        updateEdges();
        window.setTimeout(updateEdges, 320);
      });
    },
    [pauseTemporarily, updateEdges],
  );

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;

    updateEdges();
    const raf = requestAnimationFrame(() => {
      updateEdges();
      requestAnimationFrame(updateEdges);
    });

    const onScroll = () => scheduleEdges();
    el.addEventListener("scroll", onScroll, { passive: true });
    el.addEventListener("scrollend", onScroll);

    // Mobile: observe track only — per-child RO churn is expensive on weak phones.
    const ro = new ResizeObserver(() => scheduleEdges());
    ro.observe(el);
    if (!isMobile) {
      for (const child of Array.from(el.children)) {
        ro.observe(child);
      }
    }

    // IntersectionObserver only when autoplay can run — otherwise pure overhead.
    let io: IntersectionObserver | null = null;
    if (autoPlay && motionSafe) {
      io = new IntersectionObserver(
        ([entry]) => {
          setOffscreenPaused(!(entry?.isIntersecting ?? false));
        },
        { root: null, threshold: 0.05 },
      );
      io.observe(el);
    } else {
      setOffscreenPaused(false);
    }

    return () => {
      cancelAnimationFrame(raf);
      if (edgeRaf.current != null) cancelAnimationFrame(edgeRaf.current);
      el.removeEventListener("scroll", onScroll);
      el.removeEventListener("scrollend", onScroll);
      ro.disconnect();
      io?.disconnect();
    };
  }, [updateEdges, scheduleEdges, items.length, isMobile, autoPlay, motionSafe]);

  useEffect(() => {
    if (
      !autoPlay ||
      !motionSafe ||
      paused ||
      hoverPaused ||
      offscreenPaused ||
      isDragging
    ) {
      return;
    }
    const el = trackRef.current;
    if (!el) return;

    const id = window.setInterval(() => {
      const edges = readHorizontalScrollEdges(el);
      if (!edges.hasOverflow) return;
      const isRtl = getComputedStyle(el).direction === "rtl";
      // RTL: advance toward physical left (inline-end). LTR: toward physical right.
      const forward: 1 | -1 = isRtl ? -1 : 1;
      const canAdvance = isRtl ? edges.canScrollLeft : edges.canScrollRight;

      if (!canAdvance) {
        scrollTrackToStart(el, "smooth");
      } else {
        el.scrollBy({ left: horizontalStepDelta(el, forward), behavior: "smooth" });
      }
      requestAnimationFrame(updateEdges);
    }, intervalMs);

    return () => window.clearInterval(id);
  }, [
    autoPlay,
    motionSafe,
    paused,
    hoverPaused,
    offscreenPaused,
    isDragging,
    intervalMs,
    updateEdges,
  ]);

  useEffect(
    () => () => {
      if (resumeTimer.current) clearTimeout(resumeTimer.current);
    },
    [],
  );

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    pauseTemporarily();
    // Touch uses native overflow pan; custom drag is mouse/pen only.
    if (e.pointerType === "touch") return;
    if (e.button !== 0) return;
    const el = trackRef.current;
    if (!el) return;
    // A prior drag can set suppress without a following click — never leave it sticky.
    suppressClickRef.current = false;
    dragRef.current = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startScroll: el.scrollLeft,
      moved: false,
      dragging: true,
    };
  };

  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    const el = trackRef.current;
    if (!drag?.dragging || !el || drag.pointerId !== e.pointerId) return;
    const dx = e.clientX - drag.startX;
    if (!drag.moved && Math.abs(dx) < DRAG_THRESHOLD) return;
    if (!drag.moved) {
      drag.moved = true;
      setIsDragging(true);
      try {
        el.setPointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
    }
    e.preventDefault();
    // Decreasing scrollLeft → visual left in LTR and RTL engines.
    el.scrollLeft = drag.startScroll - dx;
  };

  const endDrag = (e: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    const el = trackRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    if (drag.moved) suppressClickRef.current = true;
    dragRef.current = null;
    setIsDragging(false);
    if (el?.hasPointerCapture(e.pointerId)) {
      el.releasePointerCapture(e.pointerId);
    }
    updateEdges();
  };

  const onClickCapture = (e: ReactMouseEvent<HTMLDivElement>) => {
    if (!suppressClickRef.current) return;
    suppressClickRef.current = false;
    e.preventDefault();
    e.stopPropagation();
  };

  /** Block native HTML5 image/link drag which steals the pointer gesture. */
  const onDragStart = (e: ReactDragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  // Chevrons follow overflow only — reduced-motion still gets manual controls.
  const showChevrons = showControls && hasOverflow;

  return (
    <div
      className={cn("relative min-w-0", className)}
      onWheel={pauseTemporarily}
      onMouseEnter={() => setHoverPaused(true)}
      onMouseLeave={() => setHoverPaused(false)}
    >
      <div
        ref={trackRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onClickCapture={onClickCapture}
        onDragStart={onDragStart}
        className={cn(
          // No `scroll-smooth` here — it breaks mouse-drag scrollLeft updates.
          // Chevron / autoplay pass behavior:"smooth" via the Scroll API instead.
          // overflow-y-hidden: overflow-x-auto alone can make this a 2-axis scroll
          // container (CSS), so vertical wheel gets trapped and feels like page jumps.
          // touch-manipulation (pan-x + pan-y): NOT touch-pan-x alone — that blocks
          // vertical page scroll when the gesture starts on the track (mobile lock/skip).
          "no-scrollbar h-scroll flex w-full min-w-0 overflow-x-auto overflow-y-hidden overscroll-x-contain",
          "touch-manipulation select-none cursor-grab active:cursor-grabbing",
          // Snap only when idle; skip mandatory snap on mobile (coarse) — it fights
          // vertical scroll chaining and feels like the page “skips” past sections.
          isDragging ? "snap-none" : "md:snap-x md:snap-mandatory",
          gapClass,
          trackClassName ?? "pb-1",
        )}
        style={isDragging ? { scrollSnapType: "none" } : undefined}
      >
        {items.map((child, i) => (
          <div key={i} className={cn("snap-start shrink-0", itemClassName)}>
            {child}
          </div>
        ))}
      </div>

      {showChevrons ? (
        <>
          {/* Physical right — scroll toward visual right */}
          {controls === "both" || controls === "start" ? (
            <button
              type="button"
              aria-label="به راست"
              disabled={!canScrollRight}
              onClick={() => step(1)}
              className={cn(
                "absolute right-0 top-1/2 z-10 hidden h-10 w-10 -translate-y-1/2 translate-x-1/3 place-items-center rounded-full lg:grid",
                "border border-[#5E5F5E]/10 bg-white/95 text-[#5E5F5E]",
                "shadow-[0_4px_16px_-6px_rgba(94,95,94,0.35)] lg:backdrop-blur-md",
                "transition-[transform,box-shadow,opacity,color,background-color] duration-200",
                "hover:text-[#D02327] hover:shadow-[0_8px_20px_-8px_rgba(208,35,39,0.28)]",
                "disabled:pointer-events-none disabled:opacity-35",
                controlClassName,
              )}
            >
              <ChevronRight set="light" size="small" />
            </button>
          ) : null}
          {/* Physical left — scroll toward visual left */}
          {controls === "both" || controls === "end" ? (
            <button
              type="button"
              aria-label="به چپ"
              disabled={!canScrollLeft}
              onClick={() => step(-1)}
              className={cn(
                "absolute left-0 top-1/2 z-10 hidden h-10 w-10 -translate-y-1/2 -translate-x-1/3 place-items-center rounded-full lg:grid",
                "border border-[#5E5F5E]/10 bg-white/95 text-[#5E5F5E]",
                "shadow-[0_4px_16px_-6px_rgba(94,95,94,0.35)] lg:backdrop-blur-md",
                "transition-[transform,box-shadow,opacity,color,background-color] duration-200",
                "hover:text-[#D02327] hover:shadow-[0_8px_20px_-8px_rgba(208,35,39,0.28)]",
                "disabled:pointer-events-none disabled:opacity-35",
                controlClassName,
              )}
            >
              <ChevronLeft set="light" size="small" />
            </button>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
