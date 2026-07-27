/**
 * PDP editorial helpers — D3: specs SoT lives in `specifications` JSON;
 * long `description` is editorial only (no duplicate bullet dump of specs).
 */

import type { ProductSpecifications } from "@/types/product";

const ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";
const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const BULLET_PREFIX = /^[\s*•●▪︎\-–—·]+/;

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
 * Returns null when nothing editorial remains.
 */
export function filterEditorialDescription(
  description: string | null | undefined,
  specifications: ProductSpecifications | null | undefined,
  shortDescription?: string | null,
): string | null {
  const raw = (description ?? "").replace(/\r\n/g, "\n").trim();
  if (!raw) return null;

  const shortNorm = normalizeSpecText(shortDescription);
  const wholeNorm = normalizeSpecText(raw);
  if (shortNorm && wholeNorm && shortNorm === wholeNorm) return null;

  const fingerprints = collectSpecFingerprints(specifications);
  const lines = raw.split("\n");
  const kept: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (kept.length > 0 && kept[kept.length - 1] !== "") kept.push("");
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
