import { describe, expect, it } from "vitest";
import { buildSitemapIndexXml, buildUrlsetXml, escapeXmlText } from "../xml";

describe("sitemap xml", () => {
  it("escapes reserved characters", () => {
    expect(escapeXmlText(`a&b<c>"'`)).toBe("a&amp;b&lt;c&gt;&quot;&apos;");
  });

  it("builds urlset with Persian slug", () => {
    const xml = buildUrlsetXml([
      { loc: "https://www.karzartools.com/categories/انواع-کولیس" },
    ]);
    expect(xml).toContain("<urlset");
    expect(xml).toContain("انواع-کولیس");
  });

  it("builds sitemap index", () => {
    const xml = buildSitemapIndexXml([
      { loc: "https://www.karzartools.com/sitemaps/static.xml" },
    ]);
    expect(xml).toContain("<sitemapindex");
    expect(xml).not.toContain("<urlset");
  });
});
