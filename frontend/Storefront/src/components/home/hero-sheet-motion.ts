/**
 * Shared hero banner sheet / page-turn motion.
 * Next (dir=1): incoming from left, outgoing to right — RTL «ورق خوردن» (next ←).
 * Ease is intentionally soft (less snappy) with a slightly longer settle.
 */
export const HERO_SHEET_EASE = [0.4, 0.12, 0.2, 1] as const;

export const HERO_SHEET_MS = 0.58;
export const HERO_SHEET_MS_MOBILE = 0.5;
export const HERO_SHEET_MS_REDUCED = 0.14;

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

export function heroSwipePower(offset: number, velocity: number) {
  return Math.abs(offset) * velocity;
}

export function heroSheetTransition(duration: number) {
  return {
    x: { duration, ease: HERO_SHEET_EASE },
    // Opacity only used by reduced-motion crossfade; keep in sync with x so
    // we never outrun the sheet and expose the stage underlay as a “flash”.
    opacity: { duration, ease: HERO_SHEET_EASE },
  };
}

/** Opaque stage / sheet fill — matches dark hero, never page `bg-background`. */
export const HERO_SHEET_UNDERLAY = "#1a1a1a";
