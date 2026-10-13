import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { buildFiveHeroPublishedPack } from "@/config/hero-campaign-five";
import { CampaignHeroSlide } from "@/components/home/campaign-hero-slide";

vi.mock("@/lib/hero-image-handoff", () => ({
  HeroImageHandoff: ({
    desktopSrc,
    className,
  }: {
    desktopSrc: string;
    className?: string;
  }) => (
    <div data-testid="handoff-mock" data-src={desktopSrc} className={className} />
  ),
}));

describe("CampaignHeroSlide layout", () => {
  it("uses full-bleed presentation without split desktop grid", () => {
    const pack = buildFiveHeroPublishedPack();
    const slide = pack.slides[0]!;
    const html = renderToStaticMarkup(
      <CampaignHeroSlide slide={slide} compact={false} primaryHeading />,
    );

    expect(html).toContain('data-testid="campaign-hero-fullbleed"');
    expect(html).not.toContain("lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]");
    expect(html).not.toContain("campaign-hero-desktop");
    expect(html).not.toContain("campaign-hero-compact");
    expect(html).toContain("absolute inset-0");
    expect(html).toContain("تخفیف‌های ویژه‌ی کارزار");
  });

  it("keeps mobile slide full-bleed without detached copy panel", () => {
    const pack = buildFiveHeroPublishedPack();
    const slide = pack.slides[1]!;
    const html = renderToStaticMarkup(
      <CampaignHeroSlide slide={slide} compact primaryHeading={false} />,
    );

    expect(html).toContain('data-testid="campaign-hero-fullbleed"');
    expect(html).not.toContain("flex-col bg-[#1a1a1a]");
    expect(html).toContain("ابزار اندازه‌گیری");
  });
});
