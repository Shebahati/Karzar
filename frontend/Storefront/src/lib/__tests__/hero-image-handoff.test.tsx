import { createRoot } from "react-dom/client";
import { act, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HeroImageHandoff } from "@/lib/hero-image-handoff";

const readyLog: boolean[] = [];
const loadHandlers: Array<() => void> = [];

vi.mock("@/lib/hero-background-image", () => ({
  HeroBackgroundImage: ({
    desktopSrc,
    focal,
    onLoad,
  }: {
    desktopSrc: string;
    focal: string;
    onLoad?: () => void;
  }) => {
    if (onLoad) loadHandlers.push(onLoad);
    return (
      // eslint-disable-next-line @next/next/no-img-element -- test double
      <img data-testid="hero-bg" alt="" src={desktopSrc} data-focal={focal} />
    );
  },
}));

function renderHandoff(node: ReactNode) {
  loadHandlers.length = 0;
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(node);
  });
  return { container, root };
}

function fireLastLoad() {
  const fn = loadHandlers[loadHandlers.length - 1];
  act(() => {
    fn?.();
  });
}

function fireLoadAt(index: number) {
  act(() => {
    loadHandlers[index]?.();
  });
}

afterEach(() => {
  document.body.innerHTML = "";
  readyLog.length = 0;
  loadHandlers.length = 0;
});

describe("HeroImageHandoff", () => {
  it("does not report ready before first image load", () => {
    renderHandoff(
      <HeroImageHandoff
        slideKey="a"
        desktopSrc="/a.webp"
        focal="left 10%"
        onReadyChange={(r) => readyLog.push(r)}
      />,
    );
    expect(readyLog.filter(Boolean)).toHaveLength(0);
    fireLastLoad();
    expect(readyLog.filter(Boolean).length).toBeGreaterThanOrEqual(1);
  });

  it("keeps A visible until B preload loads", () => {
    const { container, root } = renderHandoff(
      <HeroImageHandoff
        slideKey="a"
        desktopSrc="/a.webp"
        focal="left 10%"
        onReadyChange={(r) => readyLog.push(r)}
      />,
    );
    fireLastLoad();
    readyLog.length = 0;

    act(() => {
      root.render(
        <HeroImageHandoff
          slideKey="b"
          desktopSrc="/b.webp"
          focal="right 20%"
          onReadyChange={(r) => readyLog.push(r)}
        />,
      );
    });
    const visible = container.querySelectorAll('[data-testid="hero-bg"]')[0] as HTMLImageElement;
    expect(visible.src).toContain("/a.webp");
    expect(visible.getAttribute("data-focal")).toBe("left 10%");
    expect(readyLog.filter(Boolean)).toHaveLength(0);

    fireLoadAt(loadHandlers.length - 1);
    const after = container.querySelectorAll('[data-testid="hero-bg"]')[0] as HTMLImageElement;
    expect(after.src).toContain("/b.webp");
    expect(after.getAttribute("data-focal")).toBe("right 20%");
    expect(readyLog.filter(Boolean).length).toBeGreaterThanOrEqual(1);
  });

  it("ignores stale B load after target moved to C", () => {
    const { container, root } = renderHandoff(
      <HeroImageHandoff slideKey="a" desktopSrc="/a.webp" focal="left 10%" onReadyChange={() => {}} />,
    );
    fireLastLoad();

    act(() => {
      root.render(
        <HeroImageHandoff slideKey="b" desktopSrc="/b.webp" focal="b" onReadyChange={() => {}} />,
      );
    });
    const bHandlerIndex = loadHandlers.length - 1;

    act(() => {
      root.render(
        <HeroImageHandoff slideKey="c" desktopSrc="/c.webp" focal="c" onReadyChange={() => {}} />,
      );
    });
    const visible = container.querySelectorAll('[data-testid="hero-bg"]')[0] as HTMLImageElement;
    fireLoadAt(bHandlerIndex);
    expect(visible.src).toContain("/a.webp");
    for (let i = bHandlerIndex + 1; i < loadHandlers.length; i++) {
      fireLoadAt(i);
    }
    const afterC = container.querySelectorAll('[data-testid="hero-bg"]')[0] as HTMLImageElement;
    expect(afterC.src).toContain("/c.webp");
  });
});
