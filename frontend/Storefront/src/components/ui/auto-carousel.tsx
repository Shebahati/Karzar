"use client";

import {
  Children,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ChevronLeft, ChevronRight } from "react-iconly";
import { cn } from "@/lib/utils";
import { useMotionSafe } from "@/lib/use-motion-safe";

/**
 * Horizontal carousel with optional autoplay.
 * User interaction pauses autoplay briefly, then resumes.
 */
export function AutoCarousel({
  children,
  className,
  itemClassName,
  autoPlay = true,
  intervalMs = 3200,
  gapClass = "gap-3 sm:gap-4",
  showControls = true,
}: {
  children: ReactNode;
  className?: string;
  itemClassName?: string;
  autoPlay?: boolean;
  intervalMs?: number;
  gapClass?: string;
  showControls?: boolean;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const motionSafe = useMotionSafe();
  const [paused, setPaused] = useState(false);
  const resumeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const items = Children.toArray(children);

  const pauseTemporarily = useCallback(() => {
    setPaused(true);
    if (resumeTimer.current) clearTimeout(resumeTimer.current);
    resumeTimer.current = setTimeout(() => setPaused(false), 5000);
  }, []);

  const step = useCallback(
    (dir: 1 | -1) => {
      const el = trackRef.current;
      if (!el) return;
      const amount = Math.min(320, el.clientWidth * 0.7);
      const isRtl = getComputedStyle(el).direction === "rtl";
      el.scrollBy({ left: isRtl ? -dir * amount : dir * amount, behavior: "smooth" });
      pauseTemporarily();
    },
    [pauseTemporarily],
  );

  useEffect(() => {
    if (!autoPlay || !motionSafe || paused) return;
    const el = trackRef.current;
    if (!el) return;

    const id = window.setInterval(() => {
      const maxScroll = el.scrollWidth - el.clientWidth;
      if (maxScroll <= 8) return;
      const isRtl = getComputedStyle(el).direction === "rtl";
      const atEnd = isRtl ? Math.abs(el.scrollLeft) >= maxScroll - 4 : el.scrollLeft >= maxScroll - 4;
      if (atEnd) {
        el.scrollTo({ left: 0, behavior: "smooth" });
      } else {
        const delta = Math.min(280, el.clientWidth * 0.55);
        el.scrollBy({ left: isRtl ? -delta : delta, behavior: "smooth" });
      }
    }, intervalMs);

    return () => window.clearInterval(id);
  }, [autoPlay, motionSafe, paused, intervalMs]);

  useEffect(
    () => () => {
      if (resumeTimer.current) clearTimeout(resumeTimer.current);
    },
    [],
  );

  return (
    <div
      className={cn("relative", className)}
      onPointerDown={pauseTemporarily}
      onWheel={pauseTemporarily}
      onTouchStart={pauseTemporarily}
    >
      <div
        ref={trackRef}
        className={cn(
          "no-scrollbar flex snap-x snap-mandatory overflow-x-auto scroll-smooth pb-1",
          gapClass,
        )}
      >
        {items.map((child, i) => (
          <div key={i} className={cn("snap-start shrink-0", itemClassName)}>
            {child}
          </div>
        ))}
      </div>

      {showControls && motionSafe && items.length > 2 && (
        <>
          <button
            type="button"
            aria-label="بعدی"
            onClick={() => step(1)}
            className="absolute -start-2 top-1/2 z-10 hidden h-10 w-10 -translate-y-1/2 place-items-center rounded-full border border-border/60 bg-card/90 text-steel shadow-card backdrop-blur-md hover:text-primary lg:grid"
          >
            <ChevronRight set="light" size="small" />
          </button>
          <button
            type="button"
            aria-label="قبلی"
            onClick={() => step(-1)}
            className="absolute -end-2 top-1/2 z-10 hidden h-10 w-10 -translate-y-1/2 place-items-center rounded-full border border-border/60 bg-card/90 text-steel shadow-card backdrop-blur-md hover:text-primary lg:grid"
          >
            <ChevronLeft set="light" size="small" />
          </button>
        </>
      )}
    </div>
  );
}
