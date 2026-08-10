import { afterEach, describe, expect, it, vi } from "vitest";
import {
  horizontalStepDelta,
  readHorizontalScrollEdges,
  scrollTrackToStart,
} from "@/lib/scroll-edges";

function mockRect(partial: Partial<DOMRect>): DOMRect {
  return {
    x: partial.left ?? 0,
    y: partial.top ?? 0,
    width: partial.width ?? 0,
    height: partial.height ?? 0,
    top: partial.top ?? 0,
    left: partial.left ?? 0,
    bottom: (partial.top ?? 0) + (partial.height ?? 0),
    right: (partial.left ?? 0) + (partial.width ?? 0),
    toJSON() {
      return this;
    },
  };
}

describe("readHorizontalScrollEdges", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("reports no overflow when content fits", () => {
    const el = {
      scrollWidth: 400,
      clientWidth: 400,
      children: [],
      getBoundingClientRect: () => mockRect({ left: 0, width: 400 }),
    } as unknown as HTMLElement;

    expect(readHorizontalScrollEdges(el)).toEqual({
      canScrollLeft: false,
      canScrollRight: false,
      hasOverflow: false,
    });
  });

  it("detects physical left/right overflow from child boxes (RTL start)", () => {
    // Track [100..400]; first child flush to right edge, last sticks out left.
    const track = mockRect({ left: 100, width: 300 });
    const first = {
      getBoundingClientRect: () => mockRect({ left: 250, width: 150 }),
    };
    const last = {
      getBoundingClientRect: () => mockRect({ left: 40, width: 150 }),
    };
    const el = {
      scrollWidth: 900,
      clientWidth: 300,
      children: [first, last],
      getBoundingClientRect: () => track,
    } as unknown as HTMLElement;

    const edges = readHorizontalScrollEdges(el);
    expect(edges.hasOverflow).toBe(true);
    expect(edges.canScrollLeft).toBe(true);
    expect(edges.canScrollRight).toBe(false);
  });

  it("detects canScrollRight when content sticks out past the right edge", () => {
    const track = mockRect({ left: 100, width: 300 });
    const first = {
      getBoundingClientRect: () => mockRect({ left: 100, width: 150 }),
    };
    const last = {
      getBoundingClientRect: () => mockRect({ left: 360, width: 150 }),
    };
    const el = {
      scrollWidth: 900,
      clientWidth: 300,
      children: [first, last],
      getBoundingClientRect: () => track,
    } as unknown as HTMLElement;

    const edges = readHorizontalScrollEdges(el);
    expect(edges.canScrollLeft).toBe(false);
    expect(edges.canScrollRight).toBe(true);
  });
});

describe("horizontalStepDelta", () => {
  it("steps by card width + gap in the requested physical direction", () => {
    const first = {
      getBoundingClientRect: () => mockRect({ left: 0, width: 160 }),
    };
    const el = {
      clientWidth: 800,
      firstElementChild: first,
    } as unknown as HTMLElement;

    vi.spyOn(window, "getComputedStyle").mockReturnValue({
      columnGap: "12px",
      gap: "12px",
    } as CSSStyleDeclaration);

    expect(horizontalStepDelta(el, 1)).toBeCloseTo(172); // 160 + 12
    expect(horizontalStepDelta(el, -1)).toBeCloseTo(-172);
  });
});

describe("scrollTrackToStart", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("scrolls the track only via scrollBy (never scrollIntoView)", () => {
    const scrollBy = vi.fn();
    const scrollIntoView = vi.fn();
    const first = {
      getBoundingClientRect: () => mockRect({ left: 40, width: 150 }),
      scrollIntoView,
    };
    const el = {
      firstElementChild: first,
      getBoundingClientRect: () => mockRect({ left: 100, width: 300 }),
      scrollBy,
      scrollTo: vi.fn(),
    } as unknown as HTMLElement;

    vi.spyOn(window, "getComputedStyle").mockReturnValue({
      direction: "ltr",
    } as CSSStyleDeclaration);

    scrollTrackToStart(el, "auto");

    expect(scrollIntoView).not.toHaveBeenCalled();
    expect(scrollBy).toHaveBeenCalledWith({ left: -60, behavior: "auto" });
  });

  it("aligns to physical right (inline-start) in RTL", () => {
    const scrollBy = vi.fn();
    const first = {
      getBoundingClientRect: () => mockRect({ left: 200, width: 150 }), // right = 350
    };
    const el = {
      firstElementChild: first,
      getBoundingClientRect: () => mockRect({ left: 100, width: 300 }), // right = 400
      scrollBy,
      scrollTo: vi.fn(),
    } as unknown as HTMLElement;

    vi.spyOn(window, "getComputedStyle").mockReturnValue({
      direction: "rtl",
    } as CSSStyleDeclaration);

    scrollTrackToStart(el, "smooth");

    // child.right (350) - track.right (400) = -50
    expect(scrollBy).toHaveBeenCalledWith({ left: -50, behavior: "smooth" });
  });
});
