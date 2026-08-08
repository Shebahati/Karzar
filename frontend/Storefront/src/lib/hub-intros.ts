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
 * Live L1 categories + older Persian path segments → intros.json hub keys (latin L1).
 */
const SLUG_ALIASES: Record<string, string> = {
  "اندازه-گیری-دقیق": "andaze-giri-daghigh",
  "اندازه-گیری-آزمایشگاهی": "andaze-giri-azmayeshgahi",
  "اندازه-گیری-فرز-cnc": "andaze-giri-cnc",
  "cnc-اندازه-گیری": "andaze-giri-cnc",
  "ابزار-اینسرتی": "abzar-inserti",
  اینسرت: "insert",
  "ابزار-انگشتی": "abzar-angoshti",
  مته: "mete",
  مته‌ها: "mete",
  قلاویز: "ghalaviz",
  ابزارگیر: "abzargir",
  "ابزار-گیر": "abzargir",
  "ابزار-گیرشی": "abzar-gireshi",
  "ابزار-کارگاهی": "abzar-kargahi",
  "دستگاههای-صنعتی": "dastgah-sanati",
  "دستگاه‌های-صنعتی": "dastgah-sanati",
  "لوازم-جانبی-صنعتی": "lavazem-janebi",
  // latin keys also resolve if intros still used Persian (defensive)
  "andaze-giri-daghigh": "andaze-giri-daghigh",
  "andaze-giri-azmayeshgahi": "andaze-giri-azmayeshgahi",
  "andaze-giri-cnc": "andaze-giri-cnc",
  "abzar-inserti": "abzar-inserti",
  insert: "insert",
  "abzar-angoshti": "abzar-angoshti",
  mete: "mete",
  ghalaviz: "ghalaviz",
  abzargir: "abzargir",
  "abzar-gireshi": "abzar-gireshi",
  "dastgah-sanati": "dastgah-sanati",
  "lavazem-janebi": "lavazem-janebi",
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
