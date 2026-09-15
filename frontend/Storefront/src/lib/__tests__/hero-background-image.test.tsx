import { createRoot } from "react-dom/client";
import { act, type ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";
import {
  HeroBackgroundImage,
  buildHeroBackgroundPictureSources,
} from "@/lib/hero-background-image";

const desktop = "/images/hero/v2/desktop/hero-special-offers.png";
const mobile = "/images/hero/v2/mobile/hero-special-offers-mobile.png";

function renderIntoContainer(node: ReactNode) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  act(() => {
    createRoot(container).render(node);
  });
  return container;
}

describe("buildHeroBackgroundPictureSources", () => {
  it("returns null when mobile art is absent", () => {
    expect(buildHeroBackgroundPictureSources({ desktopSrc: desktop })).toBeNull();
  });

  it("emits Next optimizer URLs for mobile and desktop srcsets", () => {
    const built = buildHeroBackgroundPictureSources({
      desktopSrc: desktop,
      mobileSrc: mobile,
      priority: true,
    });
    expect(built).not.toBeNull();
    expect(built!.mobileSrcSet).toContain("/_next/image?");
    expect(built!.mobileSrcSet).not.toContain(`${mobile} `);
    expect(built!.desktop.srcSet).toContain("/_next/image?");
    expect(built!.desktop.src).toContain("/_next/image?");
  });

  it("does not point mobile source at raw static PNG path", () => {
    const built = buildHeroBackgroundPictureSources({
      desktopSrc: desktop,
      mobileSrc: mobile,
    });
    expect(built!.mobileSrcSet.startsWith("/images/hero/")).toBe(false);
  });

  it("retains intrinsic width and height from desktop getImageProps", () => {
    const built = buildHeroBackgroundPictureSources({
      desktopSrc: desktop,
      mobileSrc: mobile,
      priority: true,
    });
    expect(built!.desktop.width).toBe(1672);
    expect(built!.desktop.height).toBe(941);
  });

  it("marks priority builds eager with high fetch priority and non-priority lazy", () => {
    const hi = buildHeroBackgroundPictureSources({
      desktopSrc: desktop,
      mobileSrc: mobile,
      priority: true,
    });
    expect(hi!.loading).toBe("eager");
    expect(hi!.desktop.fetchPriority).toBe("high");

    const lo = buildHeroBackgroundPictureSources({
      desktopSrc: desktop,
      mobileSrc: mobile,
      priority: false,
    });
    expect(lo!.loading).toBe("lazy");
    expect(lo!.desktop.fetchPriority).toBeUndefined();
  });
});

describe("HeroBackgroundImage", () => {
  let container: HTMLDivElement;

  afterEach(() => {
    container?.remove();
  });

  const fallback = <div data-testid="hero-fallback">fallback</div>;

  it("keeps full-bleed geometry when caller passes object-cover only", () => {
    container = renderIntoContainer(
      <HeroBackgroundImage
        desktopSrc={desktop}
        mobileSrc={mobile}
        className="object-cover"
        fallback={fallback}
      />,
    );
    const img = container.querySelector("picture img");
    expect(img).not.toBeNull();
    expect(img!.className).toContain("absolute");
    expect(img!.className).toContain("inset-0");
    expect(img!.className).toContain("h-full");
    expect(img!.className).toContain("w-full");
    expect(img!.className).toContain("object-cover");
  });

  it("renders width and height on the img element", () => {
    container = renderIntoContainer(
      <HeroBackgroundImage desktopSrc={desktop} mobileSrc={mobile} fallback={fallback} />,
    );
    const img = container.querySelector("picture img") as HTMLImageElement;
    expect(img.getAttribute("width")).toBe("1672");
    expect(img.getAttribute("height")).toBe("941");
  });

  it("uses eager loading and high fetch priority only when priority is true", () => {
    container = renderIntoContainer(
      <HeroBackgroundImage
        desktopSrc={desktop}
        mobileSrc={mobile}
        priority
        fallback={fallback}
      />,
    );
    const eagerImg = container.querySelector("picture img") as HTMLImageElement;
    expect(eagerImg.loading).toBe("eager");
    expect(eagerImg.getAttribute("fetchpriority")).toBe("high");

    container.remove();
    container = renderIntoContainer(
      <HeroBackgroundImage
        desktopSrc={desktop}
        mobileSrc={mobile}
        priority={false}
        fallback={fallback}
      />,
    );
    const lazyImg = container.querySelector("picture img") as HTMLImageElement;
    expect(lazyImg.loading).toBe("lazy");
    expect(lazyImg.getAttribute("fetchpriority")).not.toBe("high");
  });

  it("keeps mobile source on Next optimizer URLs", () => {
    container = renderIntoContainer(
      <HeroBackgroundImage desktopSrc={desktop} mobileSrc={mobile} fallback={fallback} />,
    );
    const source = container.querySelector("picture source");
    expect(source?.getAttribute("srcset")).toContain("/_next/image?");
    expect(source?.getAttribute("srcset")).not.toMatch(/\/images\/hero\/v2\/mobile\//);
  });

  it("does not force decoding=sync on the LCP image", () => {
    container = renderIntoContainer(
      <HeroBackgroundImage
        desktopSrc={desktop}
        mobileSrc={mobile}
        priority
        fallback={fallback}
      />,
    );
    const img = container.querySelector("picture img") as HTMLImageElement;
    expect(img.getAttribute("decoding")).not.toBe("sync");
    expect(img.decoding).toBe("async");
  });

  it("shows fallback after image error", () => {
    container = renderIntoContainer(
      <HeroBackgroundImage desktopSrc={desktop} mobileSrc={mobile} fallback={fallback} />,
    );
    const img = container.querySelector("picture img") as HTMLImageElement;
    expect(container.querySelector("[data-testid='hero-fallback']")).toBeNull();

    act(() => {
      img.dispatchEvent(new Event("error", { bubbles: true }));
    });

    expect(container.querySelector("[data-testid='hero-fallback']")).not.toBeNull();
    expect(container.querySelector("picture img")).toBeNull();
  });
});
