/**
 * Static pages draft layer (admin-only).
 *
 * Current adapter: localStorage (browser-only, per-device).
 * Does NOT publish to Storefront. Live Contact/About/Terms/Privacy stay
 * on hardcoded FE until BE `/cms/static-pages` (or JSON publish) ships.
 *
 * See `StaticPagesApiStub` in `@/types/static-pages`.
 */

import {
  createDefaultPage,
  createDefaultStaticPages,
} from "@/features/static-pages/defaults";
import type {
  StaticPageDocument,
  StaticPageSlug,
  StaticPagesStore,
} from "@/types/static-pages";
import { STATIC_PAGE_META } from "@/types/static-pages";

export const STATIC_PAGES_STORAGE_KEY = "karzar.admin.static-pages.v1";

const SLUGS = Object.keys(STATIC_PAGE_META) as StaticPageSlug[];

function isSlug(value: unknown): value is StaticPageSlug {
  return typeof value === "string" && SLUGS.includes(value as StaticPageSlug);
}

function isSectionShape(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  const s = value as Record<string, unknown>;
  return (
    typeof s.id === "string" &&
    typeof s.title === "string" &&
    Array.isArray(s.paragraphs) &&
    s.paragraphs.every((p) => typeof p === "string")
  );
}

function isPageShape(value: unknown): value is StaticPageDocument {
  if (!value || typeof value !== "object") return false;
  const p = value as Record<string, unknown>;
  return (
    isSlug(p.slug) &&
    typeof p.title === "string" &&
    typeof p.eyebrow === "string" &&
    typeof p.intro === "string" &&
    Array.isArray(p.sections) &&
    p.sections.every(isSectionShape) &&
    typeof p.updatedAt === "string"
  );
}

function mergeWithDefaults(raw: unknown): StaticPagesStore {
  const defaults = createDefaultStaticPages();
  if (!raw || typeof raw !== "object") return defaults;
  const parsed = raw as Partial<StaticPagesStore>;
  const pages = { ...defaults.pages };
  if (parsed.pages && typeof parsed.pages === "object") {
    for (const slug of SLUGS) {
      const candidate = parsed.pages[slug];
      if (isPageShape(candidate) && candidate.slug === slug) {
        pages[slug] = candidate;
      }
    }
  }
  return { version: 1, pages };
}

function readStore(): StaticPagesStore {
  if (typeof window === "undefined") return createDefaultStaticPages();
  try {
    const raw = window.localStorage.getItem(STATIC_PAGES_STORAGE_KEY);
    if (!raw) return createDefaultStaticPages();
    return mergeWithDefaults(JSON.parse(raw) as unknown);
  } catch {
    return createDefaultStaticPages();
  }
}

function writeStore(store: StaticPagesStore): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STATIC_PAGES_STORAGE_KEY, JSON.stringify(store));
}

export const staticPagesService = {
  list(): StaticPageDocument[] {
    const store = readStore();
    return SLUGS.map((slug) => store.pages[slug]);
  },

  get(slug: StaticPageSlug): StaticPageDocument {
    return readStore().pages[slug] ?? createDefaultPage(slug);
  },

  save(doc: StaticPageDocument): StaticPageDocument {
    if (!isSlug(doc.slug)) {
      throw new Error("slug نامعتبر است");
    }
    const store = readStore();
    const next: StaticPageDocument = {
      ...doc,
      slug: doc.slug,
      sections: doc.sections.map((s) => ({
        ...s,
        paragraphs: s.paragraphs.length ? s.paragraphs : [""],
      })),
      updatedAt: new Date().toISOString(),
    };
    store.pages[doc.slug] = next;
    writeStore(store);
    return next;
  },

  reset(slug: StaticPageSlug): StaticPageDocument {
    const store = readStore();
    const next = createDefaultPage(slug);
    store.pages[slug] = next;
    writeStore(store);
    return next;
  },

  resetAll(): StaticPagesStore {
    const store = createDefaultStaticPages();
    writeStore(store);
    return store;
  },

  /** JSON export for hand-off to BE / future publish pipeline. */
  exportJson(slug?: StaticPageSlug): string {
    const store = readStore();
    if (slug) {
      return JSON.stringify(store.pages[slug], null, 2);
    }
    return JSON.stringify(store, null, 2);
  },
};
