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
    expect(html).not.toMatch(/data-testid="campaign-hero-desktop"(?!-copy)/);
    expect(html).not.toContain("campaign-hero-compact");
    expect(html).toContain("absolute inset-0");
    expect(html).toContain("دستگاه‌های صنعتی");
  });

  it("stacks compact media and copy in separate regions", () => {
    const pack = buildFiveHeroPublishedPack();
    const slide = pack.slides[1]!;
    const html = renderToStaticMarkup(
      <CampaignHeroSlide slide={slide} compact primaryHeading={false} />,
    );

    expect(html).toContain('data-testid="campaign-hero-compact"');
    expect(html).toContain('data-testid="campaign-hero-compact-media"');
    expect(html).not.toContain('data-testid="campaign-hero-fullbleed"');
    expect(html).toContain("فرز انگشتی");
  });

  it("uses shared desktop copy safe shell with RTL stack (no magic top percentages)", () => {
    const pack = buildFiveHeroPublishedPack();
    const slide = pack.slides[0]!;
    const html = renderToStaticMarkup(
      <CampaignHeroSlide slide={slide} compact={false} primaryHeading />,
    );
    expect(html).toContain('data-testid="campaign-hero-desktop-copy-shell"');
    expect(html).toMatch(
      /data-testid="campaign-hero-desktop-copy-shell"[^>]*dir="ltr"/,
    );
    expect(html).toMatch(
      /data-testid="campaign-hero-desktop-copy-column"[^>]*dir="rtl"/,
    );
    expect(html).toContain('data-testid="campaign-hero-copy-stack"');
    expect(html).not.toMatch(/top-\[3[0-9]%/);
    expect(html).not.toContain("top-1/2");
    expect(html).not.toContain("-translate-y-1/2");
  });

  it("renders H03 dual CTA row in desktop shell", () => {
    const pack = buildFiveHeroPublishedPack();
    const h03 = pack.slides.find((s) => s.config.linkedOrbKey === "inserts")!;
    const html = renderToStaticMarkup(
      <CampaignHeroSlide slide={h03} compact={false} primaryHeading={false} />,
    );
    expect(html).toContain('data-testid="campaign-hero-cta-row"');
    expect(html).toContain("مشاهده اینسرت‌ها");
    expect(html).toContain("مشاهده ابزارهای اینسرتی");
  });
});
