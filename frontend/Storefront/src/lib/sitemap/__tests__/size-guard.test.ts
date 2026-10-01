import { describe, expect, it } from "vitest";
import { buildUrlsetXml } from "../xml";

describe("sitemap size guard", () => {
  it("1000 canonical product URLs stay well below 50MB", () => {
    const entries = Array.from({ length: 1000 }, (_, i) => ({
      loc: `https://www.karzartools.com/product/seo-crawl-${String(i).padStart(4, "0")}`,
      lastmod: "2026-06-01T09:00:00.000Z",
    }));
    const xml = buildUrlsetXml(entries);
    const bytes = new TextEncoder().encode(xml).byteLength;
    expect(bytes).toBeLessThan(5_000_000);
  });
});
