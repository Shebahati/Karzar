import { describe, expect, it } from "vitest";
import { buildFiveHeroPublishedPack } from "@/config/hero-campaign-five";
import {
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
});
