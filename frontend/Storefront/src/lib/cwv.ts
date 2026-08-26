/**
 * Core Web Vitals budgets + shared image props for home / PDP / PLP (PERF-001).
 * Lab/field targets align with Google "good" thresholds.
 */

export const CWV_BUDGETS = {
  /** LCP ≤ 2.5s (mobile p75 field or lab). */
  lcpMs: 2500,
  /** CLS ≤ 0.1. */
  cls: 0.1,
  /** INP ≤ 200ms (good). */
  inpMs: 200,
} as const;

/** LCP / above-the-fold stills — prefer bytes over max fidelity. */
export const LCP_IMAGE_QUALITY = 75;

/** Full-bleed home hero backgrounds — allowlisted in next.config qualities. */
export const HERO_IMAGE_QUALITY = 90;

/** Below-fold / gallery thumbs. */
export const CONTENT_IMAGE_QUALITY = 75;

/** First N PLP cards are typically above the fold (2-col mobile / 4-col xl). */
export const PLP_LCP_CARD_COUNT = 4;

export type LcpImageProps = {
  priority: true;
  fetchPriority: "high";
  quality: typeof LCP_IMAGE_QUALITY;
};

export type LazyImageProps = {
  loading: "lazy";
  quality: typeof CONTENT_IMAGE_QUALITY;
};

/** Props for the element expected to be LCP (hero slide 0, PDP primary, first PLP cards). */
export function lcpImageProps(): LcpImageProps {
  return {
    priority: true,
    fetchPriority: "high",
    quality: LCP_IMAGE_QUALITY,
  };
}

export function lazyImageProps(): LazyImageProps {
  return {
    loading: "lazy",
    quality: CONTENT_IMAGE_QUALITY,
  };
}

export function isPlpLcpIndex(index: number, limit = PLP_LCP_CARD_COUNT): boolean {
  return index >= 0 && index < limit;
}

export function meetsLcpBudget(lcpMs: number): boolean {
  return Number.isFinite(lcpMs) && lcpMs <= CWV_BUDGETS.lcpMs;
}

export function meetsClsBudget(cls: number): boolean {
  return Number.isFinite(cls) && cls <= CWV_BUDGETS.cls;
}

export function meetsInpBudget(inpMs: number): boolean {
  return Number.isFinite(inpMs) && inpMs <= CWV_BUDGETS.inpMs;
}
