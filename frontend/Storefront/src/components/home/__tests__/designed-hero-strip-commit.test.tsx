import { createRoot } from "react-dom/client";
import { act, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buildFiveHeroPublishedPack } from "@/config/hero-campaign-five";
import { DesignedHero } from "@/components/home/designed-hero";

const xSetCalls: number[] = [];
const commitOrderEvents: string[] = [];
let completeStripSettle: (() => void) | undefined;

vi.mock("framer-motion", () => {
  const strip = ({ children }: { children?: ReactNode }) => children ?? null;
  return {
    AnimatePresence: strip,
    motion: {
      div: ({
        children,
        className,
        ...rest
      }: {
        children?: ReactNode;
        className?: string;
      }) => (
        <div className={className} data-testid="hero-motion-track" {...rest}>
          {children}
        </div>
      ),
    },
    useMotionValue: () => ({
      get: () => 0,
      set: (v: number) => {
        if (v === 0) {
          const title = visibleHeroTitle(document.body);
          if (title !== "ابزار اندازه‌گیری") {
            throw new Error(`x-reset before destination commit (visible=${title ?? "none"})`);
          }
          commitOrderEvents.push("x-reset");
        }
        xSetCalls.push(v);
      },
      stop: () => {},
    }),
    animate: vi.fn((_mv, target: number, opts?: { onComplete?: () => void }) => {
      if (target === 0) {
        opts?.onComplete?.();
        return;
      }
      completeStripSettle = () => {
        commitOrderEvents.push("settle-complete");
        opts?.onComplete?.();
      };
    }),
  };
});

vi.mock("@/lib/hero-image-handoff", () => ({
  HeroImageHandoff: () => <div data-testid="handoff" />,
}));

function mockMobileMedia(reducedMotion = false) {
  vi.stubGlobal(
    "matchMedia",
    (query: string) => ({
      matches:
        query === "(prefers-reduced-motion: reduce)"
          ? reducedMotion
          : query === "(max-width: 767px)" || query === "(max-width: 1023px)",
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => true,
    }),
  );
}

class MockResizeObserver {
  private readonly cb: ResizeObserverCallback;
  constructor(cb: ResizeObserverCallback) {
    this.cb = cb;
  }
  observe(el: Element) {
    Object.defineProperty(el, "clientWidth", {
      value: 390,
      configurable: true,
    });
    this.cb([], this as ResizeObserver);
  }
  unobserve() {}
  disconnect() {}
}

function visibleHeroTitle(container: HTMLElement): string | undefined {
  const titles = container.querySelectorAll("h1, h2");
  for (const el of titles) {
    if (!el.closest('[aria-hidden="true"]')) return el.textContent?.trim();
  }
  return undefined;
}

function heroStripShell(container: HTMLElement): HTMLElement | null {
  return container.querySelector(".grid.grid-cols-1");
}

function nextSlideButton(container: HTMLElement): HTMLButtonElement | undefined {
  return Array.from(container.querySelectorAll("button")).find(
    (b) => b.getAttribute("aria-label") === "اسلاید بعدی",
  ) as HTMLButtonElement | undefined;
}

function mountHero(reducedMotion = false) {
  mockMobileMedia(reducedMotion);
  const pack = buildFiveHeroPublishedPack();
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(<DesignedHero pack={pack} />);
  });
  return { container, root, pack };
}

afterEach(() => {
  document.body.innerHTML = "";
  xSetCalls.length = 0;
  commitOrderEvents.length = 0;
  completeStripSettle = undefined;
  vi.unstubAllGlobals();
});

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", MockResizeObserver);
});

describe("DesignedHero mobile campaign strip commit", () => {
  it("commits destination only after settle completes, then resets x", async () => {
    const { container } = mountHero();
    expect(visibleHeroTitle(container)).toBe("تخفیف‌های ویژه‌ی کارزار");

    const nextBtn = nextSlideButton(container)!;
    await act(async () => {
      nextBtn.click();
      await Promise.resolve();
    });

    expect(visibleHeroTitle(container)).toBe("تخفیف‌های ویژه‌ی کارزار");
    expect(xSetCalls).not.toContain(0);

    await act(async () => {
      completeStripSettle?.();
      await Promise.resolve();
    });

    expect(commitOrderEvents).toEqual(["settle-complete", "x-reset"]);
    expect(visibleHeroTitle(container)).toBe("ابزار اندازه‌گیری");
  });

  it("does not show the previous slide after strip x resets to 0", async () => {
    const { container } = mountHero();
    const nextBtn = nextSlideButton(container)!;

    await act(async () => {
      nextBtn.click();
      await Promise.resolve();
      completeStripSettle?.();
      await Promise.resolve();
    });

    expect(xSetCalls).toContain(0);
    expect(visibleHeroTitle(container)).toBe("ابزار اندازه‌گیری");
    expect(visibleHeroTitle(container)).not.toBe("تخفیف‌های ویژه‌ی کارزار");
  });

  it("mounts image-free geometry sizers and only strip panels load handoff", () => {
    const { container } = mountHero();
    const shell = heroStripShell(container)!;

    const geometrySizers = shell.querySelectorAll('[data-testid="campaign-hero-geometry-sizer"]');
    expect(geometrySizers).toHaveLength(5);

    const sizerHandoffs = shell.querySelectorAll(
      '[data-testid="campaign-hero-geometry-sizer"] [data-testid="handoff"]',
    );
    expect(sizerHandoffs).toHaveLength(0);

    const stripHandoffs = container.querySelectorAll(
      '[data-testid="hero-motion-track"] [data-testid="handoff"]',
    );
    expect(stripHandoffs.length).toBe(3);
    expect(container.querySelectorAll('[data-testid="handoff"]').length).toBe(3);
  });

  it("uses shared max-height grid shell with absolute strip panels", () => {
    const { container } = mountHero();
    const shell = heroStripShell(container);
    expect(shell).toBeTruthy();

    const sizers = Array.from(shell!.children).filter(
      (el) => el.getAttribute("aria-hidden") === "true",
    );
    expect(sizers).toHaveLength(5);
    expect(
      sizers.every((el) =>
        el.querySelector('[data-testid="campaign-hero-geometry-sizer"]'),
      ),
    ).toBe(true);

    const track = container.querySelector("[data-testid=hero-motion-track]");
    expect(track!.querySelectorAll(".absolute.inset-0").length).toBeGreaterThanOrEqual(3);
  });
});

describe("DesignedHero mobile reduced-motion compact", () => {
  it("commits next slide without strip pending gate", async () => {
    const { container } = mountHero(true);
    expect(
      container.querySelectorAll('[data-testid="campaign-hero-geometry-sizer"]'),
    ).toHaveLength(5);
    expect(container.querySelector(".grid.grid-cols-1")).toBeTruthy();
    expect(container.querySelectorAll('[data-testid="handoff"]').length).toBe(1);

    const nextBtn = nextSlideButton(container)!;
    await act(async () => {
      nextBtn.click();
      await Promise.resolve();
    });

    expect(visibleHeroTitle(container)).toBe("ابزار اندازه‌گیری");
  });
});
