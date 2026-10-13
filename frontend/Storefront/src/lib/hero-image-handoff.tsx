"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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

type VisualCandidate = {
  slideKey: string;
  desktopSrc: string;
  mobileSrc: string | null | undefined;
  focal: string;
  compactMedia: boolean;
};

function sameCandidate(a: VisualCandidate, b: VisualCandidate): boolean {
  return (
    a.slideKey === b.slideKey &&
    a.desktopSrc === b.desktopSrc &&
    a.focal === b.focal &&
    a.mobileSrc === b.mobileSrc &&
    a.compactMedia === b.compactMedia
  );
}

function propsToCandidate(p: HandoffProps): VisualCandidate {
  return {
    slideKey: p.slideKey,
    desktopSrc: p.desktopSrc,
    mobileSrc: p.mobileSrc,
    focal: p.focal,
    compactMedia: Boolean(p.compactMedia),
  };
}

/**
 * Keeps the last fully decoded visual candidate (src + focal + art direction)
 * until the next candidate is ready — avoids mixed old/new metadata during load.
 */
export function HeroImageHandoff(props: HandoffProps) {
  const {
    priority,
    onReadyChange,
    className,
    imageClassName,
    compactMedia,
  } = props;
  const incoming = propsToCandidate(props);
  const [shown, setShown] = useState<VisualCandidate>(() => incoming);
  const shownRef = useRef(shown);
  shownRef.current = shown;

  const ready = sameCandidate(shown, incoming);

  useEffect(() => {
    onReadyChange?.(ready);
  }, [ready, onReadyChange]);

  useEffect(() => {
    if (sameCandidate(shownRef.current, incoming)) return;
    // Incoming changed — keep `shown` until hidden preload fires onLoad.
  }, [incoming]);

  const handleIncomingReady = useCallback(() => {
    setShown(incoming);
  }, [incoming]);

  const shownMobile = shown.compactMedia ? null : shown.mobileSrc;
  const incomingMobile = incoming.compactMedia ? null : incoming.mobileSrc;

  return (
    <div className={cn("relative h-full w-full overflow-hidden", className)}>
      <HeroBackgroundImage
        key={`shown-${shown.slideKey}-${shown.desktopSrc}`}
        desktopSrc={shown.desktopSrc}
        mobileSrc={shownMobile}
        focal={shown.focal}
        priority={priority && sameCandidate(shown, incoming)}
        className={imageClassName ?? "object-cover"}
        sizes={shown.compactMedia ? "100vw" : "(max-width: 1024px) 100vw, 55vw"}
      />
      {!sameCandidate(shown, incoming) ? (
        <div className="pointer-events-none absolute inset-0 opacity-0" aria-hidden>
          <HeroBackgroundImage
            key={`preload-${incoming.slideKey}-${incoming.desktopSrc}`}
            desktopSrc={incoming.desktopSrc}
            mobileSrc={incomingMobile}
            focal={incoming.focal}
            className={imageClassName ?? "object-cover"}
            sizes={incoming.compactMedia ? "100vw" : "(max-width: 1024px) 100vw, 55vw"}
            onLoad={handleIncomingReady}
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
