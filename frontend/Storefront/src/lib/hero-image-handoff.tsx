"use client";

import { useCallback, useEffect, useState } from "react";
import { HeroBackgroundImage } from "@/lib/hero-background-image";
import { cn } from "@/lib/utils";

type HandoffProps = {
  slideKey: string;
  desktopSrc: string;
  mobileSrc?: string | null;
  focal: string;
  priority?: boolean;
  onReadyChange?: (ready: boolean) => void;
  className?: string;
  imageClassName?: string;
  compactMedia?: boolean;
};

/**
 * Keeps the last decoded hero image visible until the next candidate is ready,
 * avoiding image-free frames during slide transitions.
 */
export function HeroImageHandoff({
  slideKey,
  desktopSrc,
  mobileSrc,
  focal,
  priority,
  onReadyChange,
  className,
  imageClassName,
  compactMedia,
}: HandoffProps) {
  const [shownSrc, setShownSrc] = useState(desktopSrc);
  const ready = desktopSrc === shownSrc;
  const artMobile = compactMedia ? null : mobileSrc;

  useEffect(() => {
    onReadyChange?.(ready);
  }, [ready, onReadyChange]);

  const handleLoad = useCallback(() => {
    setShownSrc(desktopSrc);
  }, [desktopSrc]);

  return (
    <div className={cn("relative h-full w-full overflow-hidden", className)}>
      <HeroBackgroundImage
        key={`shown-${shownSrc}-${slideKey}`}
        desktopSrc={shownSrc}
        mobileSrc={artMobile}
        focal={focal}
        priority={priority && shownSrc === desktopSrc}
        className={imageClassName ?? "object-cover"}
        sizes={compactMedia ? "100vw" : "(max-width: 1024px) 100vw, 55vw"}
        onLoad={shownSrc === desktopSrc ? handleLoad : undefined}
      />
      {desktopSrc !== shownSrc ? (
        <div className="pointer-events-none absolute inset-0 opacity-0" aria-hidden>
          <HeroBackgroundImage
            key={`preload-${desktopSrc}-${slideKey}`}
            desktopSrc={desktopSrc}
            mobileSrc={artMobile}
            focal={focal}
            className={imageClassName ?? "object-cover"}
            sizes={compactMedia ? "100vw" : "(max-width: 1024px) 100vw, 55vw"}
            onLoad={handleLoad}
          />
        </div>
      ) : null}
      {!ready ? (
        <span className="sr-only" aria-live="polite">
          در حال بارگذاری تصویر
        </span>
      ) : null}
    </div>
  );
}
