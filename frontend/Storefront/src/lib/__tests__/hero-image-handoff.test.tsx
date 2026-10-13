import { createRoot } from "react-dom/client";
import { act, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HeroImageHandoff } from "@/lib/hero-image-handoff";

vi.mock("@/lib/hero-background-image", () => ({
  HeroBackgroundImage: ({
    desktopSrc,
    focal,
    onLoad,
  }: {
    desktopSrc: string;
    focal: string;
    onLoad?: () => void;
  }) => (
    <img
      data-testid="hero-bg"
      alt=""
      src={desktopSrc}
      data-focal={focal}
      onLoad={onLoad}
    />
  ),
}));

function renderIntoContainer(node: ReactNode) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(node);
  });
  return { container, root };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("HeroImageHandoff", () => {
  it("keeps shown focal/src when incoming slide changes until preload loads", () => {
    const { container, root } = renderIntoContainer(
      <HeroImageHandoff slideKey="a" desktopSrc="/a.webp" focal="left 10%" />,
    );
    const first = container.querySelector('[data-testid="hero-bg"]') as HTMLImageElement;
    expect(first?.src).toContain("/a.webp");
    expect(first?.getAttribute("data-focal")).toBe("left 10%");

    act(() => {
      root.render(
        <HeroImageHandoff slideKey="b" desktopSrc="/b.webp" focal="right 20%" />,
      );
    });
    const visible = container.querySelectorAll('[data-testid="hero-bg"]')[0] as HTMLImageElement;
    expect(visible?.src).toContain("/a.webp");
    expect(visible?.getAttribute("data-focal")).toBe("left 10%");
  });
});
