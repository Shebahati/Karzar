/** Storefront PDP SEO metadata helpers (mirrors backend app.utils.seo_descriptions). */

import { stripDescriptionImages } from "@/lib/pdp-description";

const STUB_MAX_LENGTH = 40;

function norm(text: string | null | undefined): string {
  if (!text) return "";
  return text.replace(/\s+/g, " ").trim();
}

export function isStubDescription(
  text: string | null | undefined,
  productName?: string | null,
): boolean {
  const body = norm(text);
  if (!body) return true;
  if (body.length < STUB_MAX_LENGTH) return true;
  const name = norm(productName);
  if (name && body.toLocaleLowerCase("fa") === name.toLocaleLowerCase("fa")) return true;
  if (
    name &&
    body.toLocaleLowerCase("fa").startsWith(name.toLocaleLowerCase("fa")) &&
    body.length <= name.length + 8
  ) {
    return true;
  }
  return false;
}

export function excerptDescription(
  text: string | null | undefined,
  maxLen = 160,
): string | null {
  const body = norm(stripDescriptionImages(text));
  if (!body) return null;
  if (body.length <= maxLen) return body;
  let truncated = body.slice(0, maxLen - 1).trimEnd();
  const space = truncated.lastIndexOf(" ");
  if (space > 40) truncated = truncated.slice(0, space);
  return `${truncated}…`;
}

export function resolveMetaTitle(metaTitle: string | null | undefined, name: string): string {
  return norm(metaTitle) || norm(name) || "محصول";
}

export function resolveMetaDescription(opts: {
  metaDescription?: string | null;
  shortDescription?: string | null;
  description?: string | null;
  name: string;
}): string {
  const meta = norm(opts.metaDescription);
  if (meta) return meta.slice(0, 500);

  const short = norm(opts.shortDescription);
  if (short && !isStubDescription(short, opts.name)) return short.slice(0, 500);

  const excerpt = excerptDescription(opts.description) || "";
  if (excerpt && !isStubDescription(excerpt, opts.name)) return excerpt.slice(0, 500);

  if (short) return short.slice(0, 500);

  const safeName = norm(opts.name) || "این محصول";
  return `${safeName} | فروشگاه ابزار کارزار`;
}

export function resolveJsonLdDescription(opts: {
  shortDescription?: string | null;
  description?: string | null;
  name: string;
  maxLen?: number;
}): string {
  const maxLen = opts.maxLen ?? 500;
  const short = norm(opts.shortDescription);
  if (short) return short.slice(0, maxLen);
  const excerpt = excerptDescription(opts.description, maxLen);
  if (excerpt) return excerpt;
  return resolveMetaDescription({
    metaDescription: null,
    shortDescription: null,
    description: null,
    name: opts.name,
  }).slice(0, maxLen);
}
