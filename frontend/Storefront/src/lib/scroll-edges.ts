/**
 * Horizontal overflow edges mapped to physical left/right.
 *
 * RTL scrollLeft differs by engine:
 * - Chromium/Firefox: 0 at start → negative toward the end
 * - Legacy WebKit: max at start → 0 at the end
 *
 * In both models (and LTR), decreasing scrollLeft moves toward visual left;
 * increasing moves toward visual right. Buttons should bind to that.
 */

export type HorizontalScrollEdges = {
  canScrollLeft: boolean;
  canScrollRight: boolean;
  hasOverflow: boolean;
};

type RtlScrollType = "negative" | "positive" | "default";

let cachedRtlScrollType: RtlScrollType | null = null;

function detectRtlScrollType(): RtlScrollType {
  if (cachedRtlScrollType) return cachedRtlScrollType;
  if (typeof document === "undefined") return "negative";

  const outer = document.createElement("div");
  outer.appendChild(document.createTextNode("ABCD"));
  outer.dir = "rtl";
  outer.style.cssText =
    "font-size:14px;width:4px;height:1px;position:absolute;top:-1000px;overflow:scroll";
  document.body.appendChild(outer);

  let type: RtlScrollType = "negative";
  if (outer.scrollLeft > 0) {
    type = "positive";
  } else {
    outer.scrollLeft = 1;
    if (outer.scrollLeft === 0) {
      type = "negative";
    } else {
      type = "default";
    }
  }

  document.body.removeChild(outer);
  cachedRtlScrollType = type;
  return type;
}

/** Distance scrolled away from the inline-start edge (0…max). */
function distanceFromStart(scrollLeft: number, maxScroll: number, isRtl: boolean): number {
  if (!isRtl) return scrollLeft;

  switch (detectRtlScrollType()) {
    case "negative":
      return -scrollLeft;
    case "positive":
      return maxScroll - scrollLeft;
    case "default":
      return scrollLeft;
  }
}

export function readHorizontalScrollEdges(el: HTMLElement): HorizontalScrollEdges {
  const maxScroll = el.scrollWidth - el.clientWidth;
  if (maxScroll <= 2) {
    return { canScrollLeft: false, canScrollRight: false, hasOverflow: false };
  }

  const isRtl = getComputedStyle(el).direction === "rtl";
  const scrolled = distanceFromStart(el.scrollLeft, maxScroll, isRtl);
  const atStart = scrolled < 4;
  const atEnd = scrolled >= maxScroll - 4;

  // Physical sides: inline-start is right in RTL, left in LTR.
  if (isRtl) {
    return {
      // Toward inline-end (visual left / further into content)
      canScrollLeft: !atEnd,
      // Toward inline-start (visual right / back to start)
      canScrollRight: !atStart,
      hasOverflow: true,
    };
  }

  return {
    canScrollLeft: !atStart,
    canScrollRight: !atEnd,
    hasOverflow: true,
  };
}
