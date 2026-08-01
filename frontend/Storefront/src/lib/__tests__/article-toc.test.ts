import { describe, expect, it } from "vitest";
import {
  prepareArticleContent,
  slugifyHeading,
  stripEmbeddedToc,
  tocFromHtml,
  uniqueHeadingId,
} from "@/lib/article-toc";
import type { BlogBlock } from "@/types/content";

describe("article-toc", () => {
  it("slugifies Persian headings", () => {
    expect(slugifyHeading("نکتهٔ کارگاهی")).toBe("نکتهٔ-کارگاهی");
    expect(slugifyHeading("  Hello World!  ")).toBe("Hello-World");
  });

  it("dedupes heading ids", () => {
    const used = new Set<string>();
    expect(uniqueHeadingId("جمع‌بندی", used)).toBe("جمعبندی");
    expect(uniqueHeadingId("جمع‌بندی", used)).toBe("جمعبندی-2");
  });

  it("strips embedded فهرست مطالب + list", () => {
    const blocks: BlogBlock[] = [
      { type: "paragraph", text: "intro" },
      { type: "heading", text: "فهرست مطالب" },
      { type: "list", ordered: true, items: ["الف", "ب"] },
      { type: "heading", text: "کولیس چیست؟" },
      { type: "paragraph", text: "body" },
    ];
    const stripped = stripEmbeddedToc(blocks);
    expect(stripped.map((b) => ("text" in b ? b.text : b.type))).toEqual([
      "intro",
      "کولیس چیست؟",
      "body",
    ]);
  });

  it("builds toc from heading and subheading blocks", () => {
    const { toc, bodyBlocks, headingIds } = prepareArticleContent([
      { type: "paragraph", text: "lead" },
      { type: "heading", text: "بخش یک" },
      { type: "subheading", text: "زیربخش" },
      { type: "heading", text: "بخش دو" },
    ]);
    expect(toc).toHaveLength(3);
    expect(toc[0]).toMatchObject({ text: "بخش یک", level: 2 });
    expect(toc[1]).toMatchObject({ text: "زیربخش", level: 3 });
    expect(headingIds.get(1)).toBe(toc[0].id);
    expect(bodyBlocks).toHaveLength(4);
  });

  it("extracts toc from flat HTML h2/h3", () => {
    const toc = tocFromHtml(
      "<p>x</p><h2>مقدمه</h2><p>a</p><h3>جزئیات</h3><h2>فهرست مطالب</h2>",
    );
    expect(toc.map((t) => t.text)).toEqual(["مقدمه", "جزئیات"]);
    expect(toc[0].level).toBe(2);
    expect(toc[1].level).toBe(3);
  });
});
