import { getSiteUrl } from "@/lib/site-url";

const FORBIDDEN_LOC_PATTERNS = [
  /\?page=/i,
  /\?brand=/i,
  /\?search=/i,
  /\?sort=/i,
  /\?category=/i,
  /\?spec_/i,
  /\/cart\b/i,
  /\/checkout\b/i,
  /\/account\b/i,
  /\/login\b/i,
  /\/quote\b/i,
];

export function assertAbsoluteCanonicalLoc(loc: string, siteUrl: string = getSiteUrl()): void {
  let parsed: URL;
  try {
    parsed = new URL(loc);
  } catch {
    throw new Error(`Invalid sitemap loc URL: ${loc}`);
  }
  const site = new URL(siteUrl);
  if (parsed.protocol !== "https:") {
    throw new Error(`Sitemap loc must be https: ${loc}`);
  }
  if (parsed.host !== site.host) {
    throw new Error(`Sitemap loc host mismatch: ${loc}`);
  }
  if (parsed.search) {
    throw new Error(`Sitemap loc must not include query string: ${loc}`);
  }
  for (const pattern of FORBIDDEN_LOC_PATTERNS) {
    if (pattern.test(loc)) {
      throw new Error(`Forbidden sitemap loc pattern: ${loc}`);
    }
  }
}

export function assertNoDuplicateLocs(locs: string[]): void {
  const seen = new Set<string>();
  for (const loc of locs) {
    if (seen.has(loc)) {
      throw new Error(`Duplicate sitemap loc: ${loc}`);
    }
    seen.add(loc);
  }
}

export function validateUrlEntries(entries: { loc: string }[], siteUrl?: string): void {
  const locs = entries.map((e) => e.loc);
  assertNoDuplicateLocs(locs);
  for (const loc of locs) {
    assertAbsoluteCanonicalLoc(loc, siteUrl);
  }
}
