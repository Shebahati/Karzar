import { describe, expect, it } from "vitest";
import { buildHeroBackgroundPictureSources } from "@/lib/hero-background-image";

describe("buildHeroBackgroundPictureSources", () => {
  const desktop = "/images/hero/v2/desktop/hero-special-offers.png";
  const mobile = "/images/hero/v2/mobile/hero-special-offers-mobile.png";

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
});
