import type { BlogBlock } from "@/types/content";

export type ArticleTocItem = {
  id: string;
  text: string;
  level: 2 | 3;
};

/** Headings that are themselves a TOC (rendered separately as «منو»). */
const EMBEDDED_TOC_TITLE =
  /^(فهرست\s*مطالب|منوی\s*مطالب|منو|جدول\s*محتوا|contents?|table\s*of\s*contents)$/i;

export function slugifyHeading(text: string): string {
  const base = text
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^\u0600-\u06FFa-zA-Z0-9\-]/g, "")
    .slice(0, 80);
  return base || "section";
}

export function uniqueHeadingId(text: string, used: Set<string>): string {
  const base = slugifyHeading(text);
  let id = base;
  let n = 2;
  while (used.has(id)) {
    id = `${base}-${n}`;
    n += 1;
  }
  used.add(id);
  return id;
}

/**
 * Drop a manual «فهرست مطالب» heading (+ following list) so the page TOC is single-source.
 */
export function stripEmbeddedToc(blocks: BlogBlock[]): BlogBlock[] {
  const out: BlogBlock[] = [];
  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];
    if (
      (block.type === "heading" || block.type === "subheading") &&
      EMBEDDED_TOC_TITLE.test(block.text.trim())
    ) {
      if (blocks[i + 1]?.type === "list") i += 1;
      continue;
    }
    out.push(block);
  }
  return out;
}

/**
 * Extract h2/h3-style TOC entries and stable ids aligned with body heading indices.
 */
export function prepareArticleContent(blocks: BlogBlock[]): {
  toc: ArticleTocItem[];
  bodyBlocks: BlogBlock[];
  headingIds: Map<number, string>;
} {
  const bodyBlocks = stripEmbeddedToc(blocks);
  const used = new Set<string>();
  const toc: ArticleTocItem[] = [];
  const headingIds = new Map<number, string>();

  bodyBlocks.forEach((block, index) => {
    if (block.type !== "heading" && block.type !== "subheading") return;
    const id = uniqueHeadingId(block.text, used);
    headingIds.set(index, id);
    toc.push({
      id,
      text: block.text,
      level: block.type === "heading" ? 2 : 3,
    });
  });

  return { toc, bodyBlocks, headingIds };
}

/**
 * Pull heading texts from an HTML string (h2/h3) when a flat HTML body is present.
 * Does not invent content — only reads existing tags.
 */
export function tocFromHtml(html: string): ArticleTocItem[] {
  if (!html?.trim()) return [];
  const used = new Set<string>();
  const toc: ArticleTocItem[] = [];
  const re = /<h([23])\b[^>]*>([\s\S]*?)<\/h\1>/gi;
  let match: RegExpExecArray | null;
  while ((match = re.exec(html)) !== null) {
    const level = Number(match[1]) as 2 | 3;
    const text = match[2]
      .replace(/<[^>]+>/g, "")
      .replace(/&nbsp;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .trim();
    if (!text || EMBEDDED_TOC_TITLE.test(text)) continue;
    toc.push({ id: uniqueHeadingId(text, used), text, level });
  }
  return toc;
}
