import { describe, expect, it } from "vitest";
import { buildFiveHeroPublishedPack } from "@/config/hero-campaign-five";
import {
  CAMPAIGN_COMPACT_MAX_PX,
  CAMPAIGN_MOBILE_SOURCE_MAX_PX,
  COMPACT_BAND_ART_WIDTH_PX,
  COMPACT_BAND_PORTRAIT_HEIGHT_PX,
  campaignMediaForSlide,
  isRebornFiveCampaign,
} from "@/lib/hero-campaign-layout";

describe("hero campaign layout", () => {
  it("detects the published five-hero pack", () => {
    const pack = buildFiveHeroPublishedPack();
    expect(isRebornFiveCampaign(pack.slides)).toBe(true);
  });

  it("rejects unrelated slide sets", () => {
    const pack = buildFiveHeroPublishedPack();
    const trimmed = pack.slides.slice(0, 4);
    expect(isRebornFiveCampaign(trimmed)).toBe(false);
  });

  it("supplies compact media aspect per slide", () => {
    const pack = buildFiveHeroPublishedPack();
    const h05 = pack.slides.find((s) => s.config.linkedOrbKey === "industrial-machines")!;
    expect(campaignMediaForSlide(h05.id).compactAspect).toBeGreaterThan(1.5);
  });

  it("keeps mobile focal independent from desktop focal", () => {
    const pack = buildFiveHeroPublishedPack();
    const h01 = pack.slides[0]!;
    const media = campaignMediaForSlide(h01.id);
    expect(media.desktopFocal).toContain("left");
    expect(media.mobileFocal).not.toBe(media.desktopFocal);
  });

  it("aligns mobile picture breakpoint with compact layout", () => {
    expect(CAMPAIGN_MOBILE_SOURCE_MAX_PX).toBe(CAMPAIGN_COMPACT_MAX_PX);
  });

  it("documents portrait mobile art dimensions", () => {
    expect(COMPACT_BAND_ART_WIDTH_PX).toBe(1280);
    expect(COMPACT_BAND_PORTRAIT_HEIGHT_PX).toBe(1707);
  });
});
