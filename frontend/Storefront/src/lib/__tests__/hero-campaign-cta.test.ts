import { describe, expect, it } from "vitest";
import { buildFiveHeroPublishedPack } from "@/config/hero-campaign-five";
import { resolveCampaignHeroCtas } from "@/lib/hero-campaign-cta";
import type { CategoryTreeNode } from "@/types/category";

const node = (id: number, name: string, slug: string): CategoryTreeNode =>
  ({ id, name, slug, parent_id: null, subcategories: [] }) as CategoryTreeNode;

describe("approved hero CTA target safety", () => {
  const slides = buildFiveHeroPublishedPack().slides;
  const roots = [
    node(31, "اندازه‌گیری", "real-measuring-root"),
    node(32, "اینسرت", "real-inserts-root"),
    node(33, "ابزار اینسرتی", "real-insert-tools"),
    node(34, "فرز انگشتی", "real-endmills-root"),
    node(35, "دستگاه‌های صنعتی", "real-machines-root"),
  ];

  it("never routes the original five campaign buttons through hardcoded/empty category hubs", () => {
    const resolved = slides.map((slide) => resolveCampaignHeroCtas(slide, roots));
    expect(resolved.map((slide) => slide.config.buttons.map((b) => b.action.value))).toEqual([
      ["/catalog?on_sale=1"],
      ["/catalog?category=31"],
      ["/catalog?category=32", "/catalog?category=33"],
      ["/catalog?category=34"],
      ["/catalog?category=35"],
    ]);
  });
  it("fails safely to a named catalog search if category tree is unavailable or ambiguous", () => {
    const measuring = slides[1]!;
    const missing = resolveCampaignHeroCtas(measuring, []);
    expect(missing.config.buttons[0]?.action.value).toBe("/catalog?search=" + encodeURIComponent("اندازه‌گیری"));
    const ambiguous = resolveCampaignHeroCtas(measuring, [roots[0]!, node(44, "اندازه گیری", "duplicate")]);
    expect(ambiguous.config.buttons[0]?.action.value).toBe(missing.config.buttons[0]?.action.value);
  });
  it("preserves manually authored destinations and never mutates the published pack", () => {
    const measuring = structuredClone(slides[1]!);
    measuring.config.buttons[0]!.action.value = "/catalog?brand=7";
    expect(resolveCampaignHeroCtas(measuring, roots)).toBe(measuring);
    expect(slides[1]!.config.buttons[0]!.action.value).toBe("/categories/andaze-giri");
  });
});
