import { describe, expect, it } from "vitest";
import { buildFiveHeroPublishedPack } from "@/config/hero-campaign-five";
import {
  CAMPAIGN_COMPACT_MAX_PX,
  CAMPAIGN_DESKTOP_COPY_MAX_WIDTH,
  CAMPAIGN_DESKTOP_MAX_VERTICAL_NUDGE_PX,
  CAMPAIGN_DESKTOP_MIN_EDGE_MARGIN_PX,
  CAMPAIGN_COMPACT_ART_HEIGHT_PX,
  CAMPAIGN_COMPACT_ART_WIDTH_PX,
  CAMPAIGN_DESKTOP_ART_HEIGHT_PX,
  CAMPAIGN_DESKTOP_ART_WIDTH_PX,
  CAMPAIGN_MOBILE_SOURCE_MAX_PX,
  DEFAULT_COMPACT_ASPECT,
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

  it("uses 4:3 compact media for every calibrated slide", () => {
    const pack = buildFiveHeroPublishedPack();
    for (const slide of pack.slides) {
      expect(campaignMediaForSlide(slide.id).compactAspect).toBe(DEFAULT_COMPACT_ASPECT);
    }
    expect(campaignMediaForSlide("slide_h03_inserts").compactAspect).toBeCloseTo(4 / 3);
    expect(campaignMediaForSlide("slide_h05_machines").compactAspect).toBeCloseTo(4 / 3);
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

  it("documents calibrated desktop and compact master dimensions", () => {
    expect(CAMPAIGN_DESKTOP_ART_WIDTH_PX).toBe(3840);
    expect(CAMPAIGN_DESKTOP_ART_HEIGHT_PX).toBe(2160);
    expect(CAMPAIGN_COMPACT_ART_WIDTH_PX).toBe(2880);
    expect(CAMPAIGN_COMPACT_ART_HEIGHT_PX).toBe(2160);
    expect(CAMPAIGN_DESKTOP_ART_WIDTH_PX / CAMPAIGN_DESKTOP_ART_HEIGHT_PX).toBeCloseTo(16 / 9);
    expect(CAMPAIGN_COMPACT_ART_WIDTH_PX / CAMPAIGN_COMPACT_ART_HEIGHT_PX).toBeCloseTo(4 / 3);
  });

  it("treats H03 inserts as tallest compact copy reserve (two CTAs)", () => {
    const pack = buildFiveHeroPublishedPack();
    const tallest = campaignTallestCompactCopySlide(pack.slides);
    expect(tallest.config.linkedOrbKey).toBe("inserts");
    expect(campaignCompactCtaCount(tallest)).toBe(2);
    expect(pack.slides.every((s) => campaignCompactCtaCount(s) <= 2)).toBe(true);
  });

  it("reserves one shared compact aspect so slide changes do not jump", () => {
    const pack = buildFiveHeroPublishedPack();
    const aspects = new Set(
      pack.slides.map((s) => campaignMediaForSlide(s.id).compactAspect),
    );
    expect(aspects.size).toBe(1);
    expect(aspects).toEqual(new Set([DEFAULT_COMPACT_ASPECT]));
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

  it("uses physical max width token for desktop copy column", () => {
    expect(CAMPAIGN_DESKTOP_COPY_MAX_WIDTH).toContain("520px");
  });
});
