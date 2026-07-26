import { describe, expect, it } from "vitest";
import {
  countWords,
  getHubIntro,
  hubIntroExcerpt,
  hubIntroWordCount,
  listHubIntros,
} from "@/lib/hub-intros";

describe("SEO-002 hub intros", () => {
  const hubs = listHubIntros();

  it("ships exactly 15 unique top hubs", () => {
    expect(hubs).toHaveLength(15);
    const slugs = hubs.map((h) => h.slug);
    expect(new Set(slugs).size).toBe(15);
  });

  it("each hub has unique 150–300w intro and ≥3 internal links", () => {
    for (const hub of hubs) {
      const wc = hubIntroWordCount(hub);
      expect(wc, hub.slug).toBeGreaterThanOrEqual(150);
      expect(wc, hub.slug).toBeLessThanOrEqual(300);
      expect(hub.paragraphs.length, hub.slug).toBeGreaterThanOrEqual(2);
      expect(hub.links.length, hub.slug).toBeGreaterThanOrEqual(3);
      for (const link of hub.links) {
        expect(link.href.startsWith("/"), `${hub.slug} ${link.href}`).toBe(true);
        expect(link.label.trim().length, hub.slug).toBeGreaterThan(0);
      }
    }
  });

  it("never claims price or stock in intro copy", () => {
    const banned = /(قیمت|موجودی|تومان|ریال|انبار|stock|price)/i;
    for (const hub of hubs) {
      const text = hub.paragraphs.join(" ");
      // Allow explicit "این متن … قیمت … صحبت نمی‌کند" disclaimers — flag positive claims only
      const claim = /(قیمت\s+\d|موجودی\s+(دارد|ندارد)|در انبار|تومان\b|ریال\b)/i;
      expect(claim.test(text), hub.slug).toBe(false);
      expect(banned.test(hub.links.map((l) => l.label).join(" ")), hub.slug).toBe(
        false,
      );
    }
  });

  it("resolves known metrology/cutting slugs", () => {
    expect(getHubIntro("انواع-کولیس")?.name).toContain("کولیس");
    expect(getHubIntro("مته")?.links.length).toBeGreaterThanOrEqual(3);
    expect(getHubIntro("missing-slug-xyz")).toBeNull();
  });

  it("countWords and excerpt helpers", () => {
    expect(countWords("یک دو سه")).toBe(3);
    expect(countWords("")).toBe(0);
    const intro = getHubIntro("انواع-کولیس");
    expect(intro).toBeTruthy();
    const excerpt = hubIntroExcerpt(intro!, 80);
    expect(excerpt.length).toBeLessThanOrEqual(81);
  });
});
