"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

export type VisualCandidate = {
  slideKey: string;
  desktopSrc: string;
  mobileSrc: string | null | undefined;
  focal: string;
  compactMedia: boolean;
};

export function candidateId(c: VisualCandidate): string {
  return `${c.slideKey}\0${c.desktopSrc}\0${c.focal}\0${c.mobileSrc ?? ""}\0${c.compactMedia ? 1 : 0}`;
}

export function sameCandidate(a: VisualCandidate, b: VisualCandidate): boolean {
  return candidateId(a) === candidateId(b);
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
 * Keeps the last fully decoded visual candidate until the next candidate loads.
 * `ready` is true only after the incoming candidate's image has fired `onLoad`.
 */
export function HeroImageHandoff(props: HandoffProps) {
  const {
    slideKey,
    desktopSrc,
    mobileSrc,
    focal,
    compactMedia,
    priority,
    onReadyChange,
    className,
    imageClassName,
  } = props;
  const incoming = useMemo(
    () =>
      propsToCandidate({
        slideKey,
        desktopSrc,
        mobileSrc,
        focal,
        compactMedia,
      }),
    [slideKey, desktopSrc, mobileSrc, focal, compactMedia],
  );
  const incomingId = candidateId(incoming);
  const incomingRef = useRef(incoming);
  useEffect(() => {
    incomingRef.current = incoming;
  }, [incoming]);

  const [displayed, setDisplayed] = useState<VisualCandidate>(() => incoming);
  /** Candidate identity that has completed a successful image load. */
  const [loadedId, setLoadedId] = useState<string | null>(null);

  const ready = loadedId === incomingId;

  useEffect(() => {
    onReadyChange?.(ready);
  }, [ready, onReadyChange]);

  const markLoaded = useCallback((forId: string) => {
    setLoadedId((prev) => (prev === forId ? prev : forId));
  }, []);

  const handleVisibleLoad = useCallback(() => {
    const id = candidateId(displayed);
    if (id === incomingId) {
      markLoaded(incomingId);
    }
  }, [displayed, incomingId, markLoaded]);

  const handlePreloadLoad = useCallback(
    (preloadId: string) => {
      const current = incomingRef.current;
      const currentId = candidateId(current);
      if (preloadId !== currentId) return;
      setDisplayed(current);
      markLoaded(currentId);
    },
    [markLoaded],
  );

  const shownMobile = displayed.compactMedia ? null : displayed.mobileSrc;
  const incomingMobile = incoming.compactMedia ? null : incoming.mobileSrc;
  const preloading = !sameCandidate(displayed, incoming);

  return (
    <div className={cn("relative h-full w-full overflow-hidden", className)}>
      <HeroBackgroundImage
        key={`shown-${candidateId(displayed)}`}
        desktopSrc={displayed.desktopSrc}
        mobileSrc={shownMobile}
        focal={displayed.focal}
        priority={priority && !preloading}
        className={imageClassName ?? "object-cover"}
        sizes={displayed.compactMedia ? "100vw" : "(max-width: 1024px) 100vw, 55vw"}
        onLoad={handleVisibleLoad}
      />
      {preloading ? (
        <div
          className="pointer-events-none absolute inset-0 opacity-0"
          aria-hidden
        >
          <HeroBackgroundImage
            key={`preload-${incomingId}`}
            desktopSrc={incoming.desktopSrc}
            mobileSrc={incomingMobile}
            focal={incoming.focal}
            className={imageClassName ?? "object-cover"}
            sizes={incoming.compactMedia ? "100vw" : "(max-width: 1024px) 100vw, 55vw"}
            onLoad={() => handlePreloadLoad(incomingId)}
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
