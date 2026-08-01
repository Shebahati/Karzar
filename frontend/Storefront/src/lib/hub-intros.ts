/**
 * SEO-002 — category hub intros + internal links.
 * Source: content/hubs/intros.json (bundled at build time).
 */

import introsJson from "../../content/hubs/intros.json";

export type HubIntroLink = {
  href: string;
  label: string;
};

export type HubIntro = {
  slug: string;
  name: string;
  paragraphs: string[];
  links: HubIntroLink[];
};

type HubIntrosFile = {
  version: number;
  task: string;
  hubs: HubIntro[];
};

const DATA = introsJson as HubIntrosFile;

const BY_SLUG = new Map(DATA.hubs.map((hub) => [hub.slug, hub]));

/**
 * Live L1 latin slugs / alternate path segments → intros.json hub keys (Persian).
 * intros.json still uses Persian hub slugs; map live taxonomy slugs onto them.
 */
const SLUG_ALIASES: Record<string, string> = {
  "andaze-giri-daghigh": "اندازه-گیری-دقیق",
  "andaze-giri-azmayeshgahi": "اندازه-گیری-آزمایشگاهی",
  "andaze-giri-cnc": "اندازه-گیری-فرز-cnc",
  "abzar-inserti": "ابزار-اینسرتی",
  insert: "اینسرت",
  "abzar-angoshti": "ابزار-انگشتی",
  mete: "مته",
  ghalaviz: "قلاویز",
  abzargir: "ابزارگیر",
  "abzar-gireshi": "ابزار-گیرشی",
  "dastgah-sanati": "دستگاه‌های-صنعتی",
  "lavazem-janebi": "لوازم-جانبی-صنعتی",
  // older / alternate Persian path segments
  "اندازه-گیری-فرز-cnc": "اندازه-گیری-فرز-cnc",
  "cnc-اندازه-گیری": "اندازه-گیری-فرز-cnc",
};

/** Count whitespace-separated tokens (Persian/Latin). */
export function countWords(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).filter(Boolean).length;
}

export function hubIntroWordCount(intro: HubIntro): number {
  return countWords(intro.paragraphs.join(" "));
}

export function listHubIntros(): HubIntro[] {
  return DATA.hubs;
}

function resolveIntroSlug(slug: string): HubIntro | null {
  const direct = BY_SLUG.get(slug);
  if (direct) return direct;

  const aliasTarget = SLUG_ALIASES[slug];
  if (aliasTarget) {
    const viaAlias = BY_SLUG.get(aliasTarget);
    if (viaAlias) return viaAlias;
  }

  // DB sometimes appends `-{id}` to Persian slugs.
  const stripped = slug.replace(/-\d+$/u, "");
  if (stripped !== slug) {
    const viaStrip = BY_SLUG.get(stripped);
    if (viaStrip) return viaStrip;
    const aliasFromStrip = SLUG_ALIASES[stripped];
    if (aliasFromStrip) {
      const via = BY_SLUG.get(aliasFromStrip);
      if (via) return via;
    }
  }

  return null;
}

export function getHubIntro(slug: string | null | undefined): HubIntro | null {
  if (!slug) return null;
  return resolveIntroSlug(slug);
}

/** Plain excerpt for meta / JSON-LD (no invented claims). */
export function hubIntroExcerpt(intro: HubIntro, maxLen = 160): string {
  const plain = intro.paragraphs.join(" ").replace(/\s+/g, " ").trim();
  if (plain.length <= maxLen) return plain;
  let cut = plain.slice(0, maxLen - 1).trimEnd();
  const lastSpace = cut.lastIndexOf(" ");
  if (lastSpace > maxLen * 0.6) cut = cut.slice(0, lastSpace);
  return `${cut}…`;
}
