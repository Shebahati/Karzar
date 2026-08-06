/**
 * Horizontal overflow edges mapped to physical left/right.
 *
 * Avoids relying on scrollLeft alone: RTL engines disagree
 * (Chromium/Firefox negative, legacy WebKit positive-from-max).
 * Physical edges are derived from child vs track bounding boxes.
 */

export type HorizontalScrollEdges = {
  canScrollLeft: boolean;
  canScrollRight: boolean;
  hasOverflow: boolean;
};

const EDGE_PX = 2;

/**
 * Read whether the track can still scroll toward physical left / right.
 * Safe under LTR and RTL; does not depend on scrollLeft sign conventions.
 */
export function readHorizontalScrollEdges(el: HTMLElement): HorizontalScrollEdges {
  const maxScroll = el.scrollWidth - el.clientWidth;
  if (maxScroll <= EDGE_PX) {
    return { canScrollLeft: false, canScrollRight: false, hasOverflow: false };
  }

  const track = el.getBoundingClientRect();
  const children = el.children;
  if (!children.length) {
    return { canScrollLeft: false, canScrollRight: false, hasOverflow: true };
  }

  let contentLeft = Infinity;
  let contentRight = -Infinity;
  for (let i = 0; i < children.length; i++) {
    const child = children[i] as HTMLElement;
    const r = child.getBoundingClientRect();
    contentLeft = Math.min(contentLeft, r.left);
    contentRight = Math.max(contentRight, r.right);
  }

  // Content sticking out past the visible track on that physical side.
  const canScrollLeft = contentLeft < track.left - EDGE_PX;
  const canScrollRight = contentRight > track.right + EDGE_PX;

  return {
    canScrollLeft,
    canScrollRight,
    hasOverflow: true,
  };
}

/**
 * Pixel delta for one chevron step: first item width + gap, capped to ~viewport.
 * Positive = physical right; negative = physical left.
 * scrollBy({ left }) matches that in LTR and RTL (decreasing scrollLeft → left).
 */
export function horizontalStepDelta(el: HTMLElement, dir: 1 | -1): number {
  const first = el.firstElementChild as HTMLElement | null;
  const styles = getComputedStyle(el);
  const gap = Number.parseFloat(styles.columnGap || styles.gap || "0") || 0;
  const card = first?.getBoundingClientRect().width ?? 0;
  const step = card > 0 ? card + gap : Math.min(280, el.clientWidth * 0.55);
  // One card (+ gap), capped so wide viewports still move a readable chunk.
  const amount = Math.min(step, Math.max(160, el.clientWidth * 0.55));
  return dir * amount;
}

/**
 * Jump to the inline-start edge without touching document scroll.
 *
 * Do NOT use Element.scrollIntoView here: even with `block: "nearest"` it
 * scrolls every scrollable ancestor, so a partially-on-screen home carousel
 * will yank the page vertically when autoplay wraps — feels like random jumps.
 *
 * Instead scroll this track only via scrollBy, aligning the first child to
 * inline-start (physical left in LTR, physical right in RTL).
 */
export function scrollTrackToStart(
  el: HTMLElement,
  behavior: ScrollBehavior = "smooth",
): void {
  const first = el.firstElementChild as HTMLElement | null;
  if (!first) {
    el.scrollTo({ left: 0, behavior });
    return;
  }

  const track = el.getBoundingClientRect();
  const child = first.getBoundingClientRect();
  const isRtl = getComputedStyle(el).direction === "rtl";
  // Align first item to inline-start edge of the track.
  const delta = isRtl ? child.right - track.right : child.left - track.left;
  if (Math.abs(delta) < 1) return;
  el.scrollBy({ left: delta, behavior });
}
