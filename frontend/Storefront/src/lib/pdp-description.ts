/**
 * PDP editorial helpers — D3: specs SoT lives in `specifications` JSON;
 * long `description` is editorial only (no duplicate bullet dump of specs).
 *
 * Inline images: markdown `![alt](url)` or HTML `<img src="..." alt="...">`
 * on their own line — stored inside the description string (no separate BE field).
 */

import type { ProductSpecifications } from "@/types/product";

const ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";
const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const BULLET_PREFIX = /^[\s*•●▪︎\-–—·]+/;

/** Whole-line markdown image: ![alt](url) */
const MD_IMAGE_LINE = /^!\[([^\]]*)\]\(([^)\s]+)\)\s*$/;
/** Whole-line HTML img (src required; alt optional). */
const HTML_IMAGE_LINE = /^<img\b[^>]*>\s*$/i;
const HTML_SRC = /\bsrc\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))/i;
const HTML_ALT = /\balt\s*=\s*(?:"([^"]*)"|'([^']*)')/i;

export type EditorialBlock =
  | { type: "text"; text: string }
  | { type: "image"; src: string; alt: string };

function isSafeImageSrc(src: string): boolean {
  const s = src.trim();
  if (!s) return false;
  if (s.startsWith("/") && !s.startsWith("//")) return true;
  try {
    const u = new URL(s, "https://karzar.local");
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

function parseImageLine(line: string): { src: string; alt: string } | null {
  const trimmed = line.trim();
  const md = trimmed.match(MD_IMAGE_LINE);
  if (md) {
    const src = (md[2] ?? "").trim();
    if (!isSafeImageSrc(src)) return null;
    return { src, alt: (md[1] ?? "").trim() || "تصویر محصول" };
  }
  if (HTML_IMAGE_LINE.test(trimmed)) {
    const srcMatch = trimmed.match(HTML_SRC);
    const src = (srcMatch?.[1] || srcMatch?.[2] || srcMatch?.[3] || "").trim();
    if (!isSafeImageSrc(src)) return null;
    const altMatch = trimmed.match(HTML_ALT);
    const alt = (altMatch?.[1] ?? altMatch?.[2] ?? "").trim() || "تصویر محصول";
    return { src, alt };
  }
  return null;
}

export function isDescriptionImageLine(line: string): boolean {
  return parseImageLine(line) != null;
}

/** Strip image markers for SEO / JSON-LD excerpts (keep prose only). */
export function stripDescriptionImages(text: string | null | undefined): string {
  if (!text) return "";
  return text
    .replace(/\r\n/g, "\n")
    .split("\n")
    .filter((line) => !isDescriptionImageLine(line))
    .join("\n")
    .replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, "")
    .replace(/<img\b[^>]*>/gi, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/**
 * Split filtered editorial text into text + image blocks for PDP rendering.
 * Adjacent text lines are merged; images become standalone blocks.
 */
export function parseEditorialBlocks(
  editorial: string | null | undefined,
): EditorialBlock[] {
  const raw = (editorial ?? "").replace(/\r\n/g, "\n");
  if (!raw.trim()) return [];

  const blocks: EditorialBlock[] = [];
  let textBuf: string[] = [];

  const flushText = () => {
    const text = textBuf.join("\n").replace(/^\n+/, "").replace(/\n+$/, "");
    textBuf = [];
    if (text.trim()) blocks.push({ type: "text", text });
  };

  for (const line of raw.split("\n")) {
    const image = parseImageLine(line);
    if (image) {
      flushText();
      blocks.push({ type: "image", src: image.src, alt: image.alt });
      continue;
    }
    textBuf.push(line);
  }
  flushText();
  return blocks;
}

/** Collapse whitespace / digits / separators for fuzzy line matching. */
export function normalizeSpecText(text: string | null | undefined): string {
  if (!text) return "";
  let s = text.normalize("NFKC").trim();
  for (let i = 0; i < 10; i += 1) {
    s = s.split(ARABIC_DIGITS[i]!).join(String(i));
    s = s.split(PERSIAN_DIGITS[i]!).join(String(i));
  }
  s = s.replace(/[\u200c\u200d]/g, "");
  s = s.replace(/[•●▪︎]/g, " ");
  // Decimal / thousands separators → ASCII dot (before other punctuation collapse)
  s = s.replace(/[٫.]/g, ".");
  s = s.replace(/[،,]/g, "");
  s = s.replace(/[–—−]/g, "-");
  s = s.replace(/[:：=|｜]/g, " ");
  s = s.replace(/\s+/g, " ").trim();
  return s.toLocaleLowerCase("fa");
}

function addPhrase(set: Set<string>, phrase: string) {
  const n = normalizeSpecText(phrase);
  if (n.length >= 2) set.add(n);
}

/** Fingerprints of every SoT key/value pair (and labeled forms). */
export function collectSpecFingerprints(
  specifications: ProductSpecifications | null | undefined,
): Set<string> {
  const phrases = new Set<string>();
  if (!specifications) return phrases;

  const pushPair = (key: string, value: string) => {
    const k = key.trim();
    const v = String(value).trim();
    if (!k || !v) return;
    addPhrase(phrases, `${k} ${v}`);
    addPhrase(phrases, `${k}: ${v}`);
    addPhrase(phrases, `${k}：${v}`);
    addPhrase(phrases, `${k} = ${v}`);
    addPhrase(phrases, `${k} | ${v}`);
  };

  for (const item of specifications.technical_specs ?? []) {
    pushPair(item.key, item.value);
  }
  for (const item of specifications.dimensions ?? []) {
    pushPair(item.key, item.value);
    pushPair(item.key, `${item.value} mm`);
    pushPair(item.key, `${item.value}mm`);
  }
  for (const [key, value] of Object.entries(specifications.features ?? {})) {
    if (typeof value === "boolean") {
      if (value) addPhrase(phrases, key);
    } else if (typeof value === "string" && value.trim()) {
      pushPair(key, value);
    }
  }

  return phrases;
}

function stripBullet(line: string): string {
  return line.replace(BULLET_PREFIX, "").trim();
}

function lineLooksLikeSpecDump(line: string, fingerprints: Set<string>): boolean {
  const cleaned = stripBullet(line);
  if (!cleaned) return true;
  const n = normalizeSpecText(cleaned);
  if (!n) return true;
  if (fingerprints.has(n)) return true;

  // "key: value" / "key - value" after normalize already space-joined
  for (const fp of fingerprints) {
    if (fp.length < 4) continue;
    if (n === fp) return true;
    // near-exact (trailing unit noise)
    if (Math.abs(n.length - fp.length) <= 3 && (n.startsWith(fp) || fp.startsWith(n))) {
      return true;
    }
  }
  return false;
}

/**
 * Keep editorial prose; drop lines that merely restate SoT specs or echo short_description.
 * Image lines are always preserved. Returns null when nothing editorial remains.
 */
export function filterEditorialDescription(
  description: string | null | undefined,
  specifications: ProductSpecifications | null | undefined,
  shortDescription?: string | null,
): string | null {
  const raw = (description ?? "").replace(/\r\n/g, "\n").trim();
  if (!raw) return null;

  const shortNorm = normalizeSpecText(shortDescription);
  const proseOnly = stripDescriptionImages(raw);
  const wholeNorm = normalizeSpecText(proseOnly);
  const hasImages = raw.split("\n").some((l) => isDescriptionImageLine(l));
  if (shortNorm && wholeNorm && shortNorm === wholeNorm && !hasImages) return null;

  const fingerprints = collectSpecFingerprints(specifications);
  const lines = raw.split("\n");
  const kept: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (kept.length > 0 && kept[kept.length - 1] !== "") kept.push("");
      continue;
    }

    if (isDescriptionImageLine(trimmed)) {
      kept.push(trimmed);
      continue;
    }

    const lineNorm = normalizeSpecText(stripBullet(trimmed));
    if (shortNorm && lineNorm === shortNorm) continue;
    if (lineLooksLikeSpecDump(trimmed, fingerprints)) continue;

    kept.push(trimmed);
  }

  // Collapse trailing/leading blank lines
  while (kept.length > 0 && kept[0] === "") kept.shift();
  while (kept.length > 0 && kept[kept.length - 1] === "") kept.pop();

  const result = kept.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  return result || null;
}

export function hasRenderableSpecs(
  specifications: ProductSpecifications | null | undefined,
): boolean {
  if (!specifications) return false;
  const tech = specifications.technical_specs?.length ?? 0;
  const dims = specifications.dimensions?.length ?? 0;
  const feats = Object.keys(specifications.features ?? {}).length;
  return tech + dims + feats > 0;
}

/**
 * Compact key/value teasers for the PDP center column.
 * Honest SoT only — empty when specs are missing.
 */
export function pickKeySpecTeasers(
  specifications: ProductSpecifications | null | undefined,
  limit = 5,
): Array<{ key: string; value: string }> {
  if (!specifications || limit <= 0) return [];
  const items: Array<{ key: string; value: string }> = [];

  const push = (key: string, value: string) => {
    if (items.length >= limit) return;
    const k = key.trim();
    const v = String(value).trim();
    if (!k || !v) return;
    items.push({ key: k, value: v });
  };

  for (const item of specifications.technical_specs ?? []) {
    push(item.key, item.value);
  }
  for (const item of specifications.dimensions ?? []) {
    push(item.key, item.value);
  }
  for (const [key, value] of Object.entries(specifications.features ?? {})) {
    if (typeof value === "boolean") {
      if (value) push(key, "دارد");
    } else if (typeof value === "string") {
      push(key, value);
    }
  }

  return items;
}
