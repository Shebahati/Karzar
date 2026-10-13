import { createRoot } from "react-dom/client";
import { act, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buildFiveHeroPublishedPack } from "@/config/hero-campaign-five";
import { CampaignHeroSlide } from "@/components/home/campaign-hero-slide";
import { DesignedHero } from "@/components/home/designed-hero";

const readyCalls: boolean[] = [];
const loadBySrc = new Map<string, () => void>();

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
        <div className={className} {...rest}>
          {children}
        </div>
      ),
    },
    useMotionValue: () => ({ get: () => 0, set: () => {} }),
    animate: vi.fn(),
  };
});

vi.mock("@/lib/hero-background-image", () => ({
  HeroBackgroundImage: ({
    desktopSrc,
    onLoad,
  }: {
    desktopSrc: string;
    onLoad?: () => void;
  }) => {
    if (onLoad) loadBySrc.set(desktopSrc, onLoad);
    return (
      // eslint-disable-next-line @next/next/no-img-element -- test double
      <img data-testid="hero-bg" alt="" src={desktopSrc} />
    );
  },
}));

function mockDesktopMedia() {
  const mqs: Record<string, { matches: boolean; listeners: Array<() => void> }> = {
    "(prefers-reduced-motion: reduce)": { matches: false, listeners: [] },
    "(max-width: 767px)": { matches: false, listeners: [] },
    "(max-width: 1023px)": { matches: false, listeners: [] },
  };
  vi.stubGlobal(
    "matchMedia",
    (query: string) => ({
      matches: mqs[query]?.matches ?? false,
      media: query,
      addEventListener: (_: string, fn: () => void) => {
        mqs[query]?.listeners.push(fn);
      },
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => true,
    }),
  );
}

function fireLoadForSrc(part: string) {
  const entry = [...loadBySrc.entries()].find(([src]) => src.includes(part));
  act(() => {
    entry?.[1]?.();
  });
}

function visibleHeroTitle(container: HTMLElement): string | undefined {
  const titles = container.querySelectorAll("h1, h2");
  for (const el of titles) {
    if (!el.closest('[aria-hidden="true"]')) return el.textContent?.trim();
  }
  return undefined;
}

afterEach(() => {
  document.body.innerHTML = "";
  readyCalls.length = 0;
  loadBySrc.clear();
  vi.unstubAllGlobals();
});

beforeEach(() => {
  mockDesktopMedia();
});

describe("CampaignHeroSlide image readiness", () => {
  it("does not report ready before campaign slide image loads", () => {
    const pack = buildFiveHeroPublishedPack();
    const slide = pack.slides[0]!;
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    act(() => {
      root.render(
        <CampaignHeroSlide
          slide={slide}
          compact={false}
          onImageReadyChange={(r) => readyCalls.push(r)}
        />,
      );
    });
    expect(readyCalls.filter(Boolean)).toHaveLength(0);
    fireLoadForSrc("H01-special-offers");
    expect(readyCalls.filter(Boolean).length).toBeGreaterThanOrEqual(1);
  });
});

describe("DesignedHero campaign pending transition", () => {
  it("keeps H01 identity until H02 preload loads, then commits H02", () => {
    const pack = buildFiveHeroPublishedPack();
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    act(() => {
      root.render(<DesignedHero pack={pack} />);
    });
    fireLoadForSrc("H01-special-offers");

    const nextBtn = Array.from(container.querySelectorAll("button")).find(
      (b) => b.getAttribute("aria-label") === "اسلاید بعدی",
    );
    expect(nextBtn).toBeTruthy();

    act(() => {
      nextBtn!.click();
    });

    expect(visibleHeroTitle(container)).toBe("تخفیف‌های ویژه‌ی کارزار");
    const visibleBefore = container.querySelector('[data-testid="hero-bg"]') as HTMLImageElement;
    expect(visibleBefore.src).toContain("H01-special-offers");

    const dock = container.querySelector('nav[aria-label="دسته‌های پاور هیرو"]');
    expect(dock?.textContent).toContain("تخفیف‌ها");

    fireLoadForSrc("H02-measuring-tools");

    expect(visibleHeroTitle(container)).toBe("ابزار اندازه‌گیری");
    const visibleAfter = container.querySelector('[data-testid="hero-bg"]') as HTMLImageElement;
    expect(visibleAfter.src).toContain("H02-measuring-tools");
    expect(dock?.textContent).toContain("اندازه‌گیری");
  });
});
