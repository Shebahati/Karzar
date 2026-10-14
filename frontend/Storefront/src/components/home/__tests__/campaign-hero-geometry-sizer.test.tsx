import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { buildFiveHeroPublishedPack } from "@/config/hero-campaign-five";
import { CampaignHeroGeometrySizer } from "@/components/home/campaign-hero-geometry-sizer";

describe("CampaignHeroGeometrySizer", () => {
  it("does not render image handoff or img elements", () => {
    const pack = buildFiveHeroPublishedPack();
    const html = renderToStaticMarkup(
      <CampaignHeroGeometrySizer slide={pack.slides[0]!} />,
    );
    expect(html).toContain('data-testid="campaign-hero-geometry-sizer"');
    expect(html).not.toContain("handoff");
    expect(html).not.toContain("<img");
    expect(html).not.toContain("<picture");
  });

  it("reserves two CTA slots for H03 inserts", () => {
    const pack = buildFiveHeroPublishedPack();
    const h03 = pack.slides.find((s) => s.config.linkedOrbKey === "inserts")!;
    const html = renderToStaticMarkup(<CampaignHeroGeometrySizer slide={h03} />);
    expect(html).toContain('data-cta-count="2"');
    const slotCount = (html.match(/data-testid="campaign-geometry-cta-slot"/g) ?? []).length;
    expect(slotCount).toBe(2);
    expect(html).toContain("مشاهده ابزارهای اینسرتی");
  });
});
