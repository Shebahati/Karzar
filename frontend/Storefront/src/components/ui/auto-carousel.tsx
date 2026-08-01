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
import { readHorizontalScrollEdges } from "@/lib/scroll-edges";
import { cn } from "@/lib/utils";
import { useMotionSafe } from "@/lib/use-motion-safe";

const DRAG_THRESHOLD = 6;

/**
 * Horizontal carousel with optional autoplay, chevrons, and drag-to-slide.
 * User interaction / hover pauses autoplay; resumes after a short idle.
 * Click-through after a drag is suppressed so card links stay intentional.
 *
 * Drag notes:
 * - Do NOT put Tailwind `scroll-smooth` on the track — CSS smooth scrolling
 *   fights per-frame `scrollLeft` writes and makes mouse-drag feel dead.
 * - Snap is disabled while actively dragging for the same reason.
 * - Touch uses native overflow pan; mouse/pen use pointer drag.
 */
export function AutoCarousel({
  children,
  className,
  itemClassName,
  trackClassName,
  autoPlay = true,
  intervalMs = 3200,
  gapClass = "gap-3 sm:gap-4",
  showControls = true,
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
  /** Extra classes for chevron buttons (position tweaks). */
  controlClassName?: string;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const motionSafe = useMotionSafe();
  const [paused, setPaused] = useState(false);
  const [hoverPaused, setHoverPaused] = useState(false);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [hasOverflow, setHasOverflow] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const resumeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
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

  const step = useCallback(
    (dir: 1 | -1) => {
      const el = trackRef.current;
      if (!el) return;
      const amount = Math.min(320, el.clientWidth * 0.7);
      // Do not negate for RTL: Chromium already inverts scrollLeft under direction:rtl.
      el.scrollBy({ left: dir * amount, behavior: "smooth" });
      pauseTemporarily();
    },
    [pauseTemporarily],
  );

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    updateEdges();
    const onScroll = () => updateEdges();
    el.addEventListener("scroll", onScroll, { passive: true });
    const ro = new ResizeObserver(() => updateEdges());
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", onScroll);
      ro.disconnect();
    };
  }, [updateEdges, items.length]);

  useEffect(() => {
    if (!autoPlay || !motionSafe || paused || hoverPaused || isDragging) return;
    const el = trackRef.current;
    if (!el) return;

    const id = window.setInterval(() => {
      const maxScroll = el.scrollWidth - el.clientWidth;
      if (maxScroll <= 8) return;
      const isRtl = getComputedStyle(el).direction === "rtl";
      const atEnd = isRtl
        ? Math.abs(el.scrollLeft) >= maxScroll - 4
        : el.scrollLeft >= maxScroll - 4;
      if (atEnd) {
        el.scrollTo({ left: 0, behavior: "smooth" });
      } else {
        const delta = Math.min(280, el.clientWidth * 0.55);
        el.scrollBy({ left: isRtl ? -delta : delta, behavior: "smooth" });
      }
    }, intervalMs);

    return () => window.clearInterval(id);
  }, [autoPlay, motionSafe, paused, hoverPaused, isDragging, intervalMs]);

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
    // Capture only after the drag threshold so card link clicks stay reliable.
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
    // Keep the grab 1:1 — preventDefault stops link/image selection quirks.
    e.preventDefault();
    // scrollLeft delta matches pointer delta in both LTR and RTL (Chromium).
    // Decreasing scrollLeft → visual left in both models (see scroll-edges.ts).
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

  const showChevrons = showControls && hasOverflow && motionSafe;

  return (
    <div
      className={cn("relative", className)}
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
          "no-scrollbar flex overflow-x-auto overscroll-x-contain",
          "touch-pan-x select-none cursor-grab active:cursor-grabbing",
          // Snap only when idle; mandatory snap fights live drag.
          isDragging ? "snap-none" : "snap-x snap-mandatory",
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
          {/* Physical right: scroll toward higher scrollLeft (visual right / RTL start). */}
          <button
            type="button"
            aria-label="به راست"
            disabled={!canScrollRight}
            onClick={() => step(1)}
            className={cn(
              "absolute -start-2 top-1/2 z-10 hidden h-10 w-10 -translate-y-1/2 place-items-center rounded-full border border-border/50 bg-card/95 text-steel shadow-card backdrop-blur-md transition-all duration-300 lg:grid",
              "hover:text-primary disabled:pointer-events-none disabled:opacity-0",
              controlClassName,
            )}
          >
            <ChevronRight set="light" size="small" />
          </button>
          {/* Physical left: scroll toward lower scrollLeft (visual left / RTL end). */}
          <button
            type="button"
            aria-label="به چپ"
            disabled={!canScrollLeft}
            onClick={() => step(-1)}
            className={cn(
              "absolute -end-2 top-1/2 z-10 hidden h-10 w-10 -translate-y-1/2 place-items-center rounded-full border border-border/50 bg-card/95 text-steel shadow-card backdrop-blur-md transition-all duration-300 lg:grid",
              "hover:text-primary disabled:pointer-events-none disabled:opacity-0",
              controlClassName,
            )}
          >
            <ChevronLeft set="light" size="small" />
          </button>
        </>
      ) : null}
    </div>
  );
}
