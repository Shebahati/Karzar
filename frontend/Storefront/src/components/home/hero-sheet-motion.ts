/**
 * Shared hero banner sheet / page-turn motion.
 * Next (dir=1): incoming from left, outgoing to right — RTL «ورق خوردن» (next ←).
 * Ease is intentionally soft (less snappy) with a slightly longer settle.
 */
export const HERO_SHEET_EASE = [0.4, 0.12, 0.2, 1] as const;
/** Desktop dissolve + restrained nudge (spec ~650ms, ease-out). */
export const HERO_DESKTOP_EASE = [0.22, 1, 0.36, 1] as const;

export const HERO_SHEET_MS = 0.58;
export const HERO_DESKTOP_MS = 0.65;
export const HERO_SHEET_MS_MOBILE = 0.5;
export const HERO_SHEET_MS_REDUCED = 0.14;

const DESKTOP_NUDGE_PX = 16;

/** Framer swipePower threshold (offset × velocity). */
export const HERO_SWIPE_CONFIDENCE = 7200;
export const HERO_SWIPE_OFFSET = 56;

/** Soft spring for drag cancel / settle-back (gentler than prior 420/38). */
export const HERO_DRAG_SETTLE = {
  type: "spring" as const,
  stiffness: 300,
  damping: 36,
  mass: 0.95,
};

/**
 * Sheet L↔R: keep opacity at 1 and stack incoming above outgoing.
 * Never fade the exit — any transparency lets the page canvas (near-white)
 * flash between abutting transforms / unloaded images.
 */
export const heroSheetVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? "-100%" : "100%",
    opacity: 1,
    zIndex: 2,
  }),
  center: {
    x: 0,
    opacity: 1,
    zIndex: 2,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? "100%" : "-100%",
    opacity: 1,
    zIndex: 1,
  }),
};

export const heroSheetReducedVariants = {
  enter: { opacity: 0, x: 0, zIndex: 2 },
  center: { opacity: 1, x: 0, zIndex: 2 },
  exit: { opacity: 0, x: 0, zIndex: 1 },
};

/** Desktop: short translation + incoming fade; outgoing stays opaque underneath. */
export const heroSheetDesktopVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? -DESKTOP_NUDGE_PX : DESKTOP_NUDGE_PX,
    opacity: 0,
    zIndex: 2,
  }),
  center: {
    x: 0,
    opacity: 1,
    zIndex: 2,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? DESKTOP_NUDGE_PX : -DESKTOP_NUDGE_PX,
    opacity: 1,
    zIndex: 1,
  }),
};

export function heroSwipePower(offset: number, velocity: number) {
  return Math.abs(offset) * velocity;
}

export function heroSheetTransition(duration: number, desktop = false) {
  const ease = desktop ? HERO_DESKTOP_EASE : HERO_SHEET_EASE;
  return {
    x: { duration, ease },
    // Opacity only used by reduced-motion crossfade; keep in sync with x so
    // we never outrun the sheet and expose the stage underlay as a “flash”.
    opacity: { duration, ease },
  };
}

/** Opaque stage / sheet fill — matches dark hero, never page `bg-background`. */
export const HERO_SHEET_UNDERLAY = "#1a1a1a";
