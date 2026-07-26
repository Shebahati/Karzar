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

export function getHubIntro(slug: string | null | undefined): HubIntro | null {
  if (!slug) return null;
  return BY_SLUG.get(slug) ?? null;
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
