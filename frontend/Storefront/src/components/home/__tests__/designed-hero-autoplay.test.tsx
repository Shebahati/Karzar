import { createRoot, type Root } from "react-dom/client";
import { act, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buildFiveHeroPublishedPack } from "@/config/hero-campaign-five";
import { DesignedHero } from "@/components/home/designed-hero";

vi.mock("framer-motion", () => {
  const strip = ({ children }: { children?: ReactNode }) => children ?? null;
  return {
    AnimatePresence: strip,
    motion: {
      div: ({ children, className }: { children?: ReactNode; className?: string }) => (
        <div className={className}>{children}</div>
      ),
    },
    useMotionValue: () => ({ get: () => 0, set: () => {} }),
    animate: vi.fn(),
  };
});

vi.mock("@/lib/hero-image-handoff", () => ({
  HeroImageHandoff: () => <div data-testid="handoff" />,
}));

function mockDesktopMedia() {
  vi.stubGlobal(
    "matchMedia",
    (query: string) => ({
      matches:
        query === "(prefers-reduced-motion: reduce)"
          ? false
          : query.includes("max-width")
            ? false
            : false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => true,
    }),
  );
}

function autoplayButton(container: HTMLElement): HTMLButtonElement | undefined {
  return Array.from(container.querySelectorAll("button")).find((b) => {
    const label = b.getAttribute("aria-label");
    return label === "توقف پخش خودکار" || label === "ادامه پخش خودکار";
  }) as HTMLButtonElement | undefined;
}

/** React delegates `mouseenter` via bubbling `mouseover`. */
function pointerEnterHero(hero: Element) {
  act(() => {
    hero.dispatchEvent(
      new MouseEvent("mouseover", { bubbles: true, relatedTarget: document.body }),
    );
  });
}

function pointerLeaveHero(hero: Element) {
  act(() => {
    hero.dispatchEvent(
      new MouseEvent("mouseout", { bubbles: true, relatedTarget: document.body }),
    );
  });
}

function mountHero() {
  const pack = buildFiveHeroPublishedPack();
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(<DesignedHero pack={pack} />);
  });
  return { container, root };
}

let root: Root | null = null;

beforeEach(() => {
  mockDesktopMedia();
});

afterEach(() => {
  document.body.innerHTML = "";
  root = null;
  vi.unstubAllGlobals();
});

describe("DesignedHero autoplay control", () => {
  it("keeps manual control state on hover without switching to resume label", () => {
    const { container } = mountHero();
    const hero = container.querySelector('section[aria-label="هیرو کارزار"]')!;
    const btn = autoplayButton(container);
    expect(btn?.getAttribute("aria-label")).toBe("توقف پخش خودکار");
    expect(btn?.getAttribute("aria-pressed")).toBe("false");

    pointerEnterHero(hero);
    expect(btn?.getAttribute("aria-label")).toBe("توقف پخش خودکار");
    expect(btn?.getAttribute("aria-pressed")).toBe("false");

    pointerLeaveHero(hero);
    expect(btn?.getAttribute("aria-label")).toBe("توقف پخش خودکار");
  });

  it("toggles manual pause and persists across mouse leave", () => {
    const { container } = mountHero();
    const hero = container.querySelector('section[aria-label="هیرو کارزار"]')!;
    const btn = autoplayButton(container)!;

    act(() => {
      btn.click();
    });
    expect(btn.getAttribute("aria-label")).toBe("ادامه پخش خودکار");
    expect(btn.getAttribute("aria-pressed")).toBe("true");

    pointerLeaveHero(hero);
    expect(btn.getAttribute("aria-pressed")).toBe("true");

    act(() => {
      btn.click();
    });
    expect(btn.getAttribute("aria-label")).toBe("توقف پخش خودکار");
    expect(btn.getAttribute("aria-pressed")).toBe("false");
  });

  it("uses transient visibility pause without flipping manual control", () => {
    const { container } = mountHero();
    const btn = autoplayButton(container)!;
    const hidden = Object.getOwnPropertyDescriptor(document, "hidden");

    act(() => {
      Object.defineProperty(document, "hidden", { configurable: true, value: true });
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(btn.getAttribute("aria-label")).toBe("توقف پخش خودکار");
    expect(btn.getAttribute("aria-pressed")).toBe("false");

    act(() => {
      Object.defineProperty(document, "hidden", { configurable: true, value: false });
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(btn.getAttribute("aria-pressed")).toBe("false");

    if (hidden) Object.defineProperty(document, "hidden", hidden);
  });

  it("keeps manual pause across tab visibility changes", () => {
    const { container } = mountHero();
    const btn = autoplayButton(container)!;
    const hidden = Object.getOwnPropertyDescriptor(document, "hidden");

    act(() => {
      btn.click();
    });
    expect(btn.getAttribute("aria-pressed")).toBe("true");

    act(() => {
      Object.defineProperty(document, "hidden", { configurable: true, value: true });
      document.dispatchEvent(new Event("visibilitychange"));
    });
    act(() => {
      Object.defineProperty(document, "hidden", { configurable: true, value: false });
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(btn.getAttribute("aria-pressed")).toBe("true");

    if (hidden) Object.defineProperty(document, "hidden", hidden);
  });

  it("keeps focus pause while moving between hero controls", () => {
    const { container } = mountHero();
    const btn = autoplayButton(container)!;
    const nextBtn = Array.from(container.querySelectorAll("button")).find(
      (b) => b.getAttribute("aria-label") === "اسلاید بعدی",
    )!;

    act(() => {
      btn.focus();
    });
    act(() => {
      nextBtn.focus();
    });
    expect(btn.getAttribute("aria-pressed")).toBe("false");
    expect(btn.getAttribute("aria-label")).toBe("توقف پخش خودکار");
  });

  it("resumes autoplay while pointer and focus remain on the control", () => {
    vi.useFakeTimers();
    const setIntervalSpy = vi.spyOn(window, "setInterval");
    const AUTOPLAY_MS = 7000;
    const autoplayIntervalCalls = () =>
      setIntervalSpy.mock.calls.filter(([, ms]) => ms === AUTOPLAY_MS).length;

    const { container } = mountHero();
    const hero = container.querySelector('section[aria-label="هیرو کارزار"]')!;
    const btn = autoplayButton(container)!;

    expect(autoplayIntervalCalls()).toBeGreaterThanOrEqual(1);

    pointerEnterHero(hero);
    act(() => {
      btn.focus();
    });
    act(() => {
      btn.click();
    });
    expect(btn.getAttribute("aria-pressed")).toBe("true");
    expect(btn.getAttribute("aria-label")).toBe("ادامه پخش خودکار");
    const pausedCalls = autoplayIntervalCalls();

    act(() => {
      btn.click();
    });
    expect(btn.getAttribute("aria-pressed")).toBe("false");
    expect(btn.getAttribute("aria-label")).toBe("توقف پخش خودکار");
    expect(autoplayIntervalCalls()).toBeGreaterThan(pausedCalls);
    expect(vi.getTimerCount()).toBeGreaterThan(0);

    setIntervalSpy.mockRestore();
    vi.useRealTimers();
  });

  it("re-applies hover pause after leave and re-enter following explicit resume", () => {
    vi.useFakeTimers();
    const { container } = mountHero();
    const hero = container.querySelector('section[aria-label="هیرو کارزار"]')!;
    const btn = autoplayButton(container)!;

    pointerEnterHero(hero);
    act(() => {
      btn.focus();
      btn.click();
      btn.click();
    });
    expect(vi.getTimerCount()).toBeGreaterThan(0);

    pointerLeaveHero(hero);
    const runningAfterLeave = vi.getTimerCount();
    expect(runningAfterLeave).toBeGreaterThan(0);

    pointerEnterHero(hero);
    expect(vi.getTimerCount()).toBeLessThan(runningAfterLeave);

    vi.useRealTimers();
  });

  it("does not render visible ادامه/توقف control text", () => {
    const { container } = mountHero();
    const btn = autoplayButton(container)!;
    const visibleText = btn.textContent ?? "";
    expect(visibleText).not.toBe("ادامه");
    expect(visibleText).not.toBe("توقف");
    expect(btn.querySelector("svg")).toBeTruthy();
  });

  it("places autoplay control below the fixed header hit layer", () => {
    const { container } = mountHero();
    const btn = container.querySelector('[data-testid="hero-autoplay-control"]') as HTMLButtonElement;
    expect(btn).toBeTruthy();
    expect(btn.className).toContain("top-[calc(5.75rem");
    expect(btn.className).toContain("z-[45]");
    expect(btn.className).toContain("h-11");
  });
});
