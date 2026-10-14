import { describe, expect, it } from "vitest";
import { buildFiveHeroPublishedPack } from "@/config/hero-campaign-five";
import {
  CAMPAIGN_COMPACT_MAX_PX,
  CAMPAIGN_DESKTOP_MAX_VERTICAL_NUDGE_PX,
  CAMPAIGN_DESKTOP_MIN_EDGE_MARGIN_PX,
  CAMPAIGN_MOBILE_SOURCE_MAX_PX,
  COMPACT_BAND_ART_WIDTH_PX,
  COMPACT_BAND_PORTRAIT_HEIGHT_PX,
  campaignCompactCtaCount,
  campaignMediaForSlide,
  campaignTallestCompactCopySlide,
  isRebornFiveCampaign,
  usesLegacyDesktopCopyPositioning,
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

  it("treats H03 inserts as tallest compact copy reserve (two CTAs)", () => {
    const pack = buildFiveHeroPublishedPack();
    const tallest = campaignTallestCompactCopySlide(pack.slides);
    expect(tallest.config.linkedOrbKey).toBe("inserts");
    expect(campaignCompactCtaCount(tallest)).toBe(2);
    expect(pack.slides.every((s) => campaignCompactCtaCount(s) <= 2)).toBe(true);
  });

  it("assigns per-slide compact media aspect for geometry reserve", () => {
    const pack = buildFiveHeroPublishedPack();
    const aspects = new Set(
      pack.slides.map((s) => campaignMediaForSlide(s.id).compactAspect),
    );
    expect(aspects.size).toBeGreaterThan(1);
    expect(pack.slides).toHaveLength(5);
  });

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
});
