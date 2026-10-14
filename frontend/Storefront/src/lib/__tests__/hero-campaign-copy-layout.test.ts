import { describe, expect, it } from "vitest";
import { buildFiveHeroPublishedPack } from "@/config/hero-campaign-five";
import {
  CAMPAIGN_DESKTOP_MAX_VERTICAL_NUDGE_PX,
  CAMPAIGN_DESKTOP_MIN_EDGE_MARGIN_PX,
  campaignMediaForSlide,
  usesLegacyDesktopCopyPositioning,
} from "@/lib/hero-campaign-layout";

describe("hero campaign desktop copy layout", () => {
  it("does not use legacy per-slide absolute top percentages", () => {
    expect(usesLegacyDesktopCopyPositioning()).toBe(false);
    const pack = buildFiveHeroPublishedPack();
    for (const slide of pack.slides) {
      const media = campaignMediaForSlide(slide.id);
      expect(media.desktopVerticalNudgePx).toBeGreaterThanOrEqual(
        -CAMPAIGN_DESKTOP_MAX_VERTICAL_NUDGE_PX,
      );
      expect(media.desktopVerticalNudgePx).toBeLessThanOrEqual(
        CAMPAIGN_DESKTOP_MAX_VERTICAL_NUDGE_PX,
      );
      expect("desktopCopyClass" in media).toBe(false);
    }
  });

  it("documents minimum desktop edge margin contract", () => {
    expect(CAMPAIGN_DESKTOP_MIN_EDGE_MARGIN_PX).toBeGreaterThanOrEqual(48);
  });

  it("reserves two CTA slots on H03 inserts", () => {
    const pack = buildFiveHeroPublishedPack();
    const h03 = pack.slides.find((s) => s.config.linkedOrbKey === "inserts")!;
    expect(h03.config.buttons).toHaveLength(2);
  });
});
