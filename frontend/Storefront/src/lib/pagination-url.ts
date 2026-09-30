/**
 * URL pagination helpers (SEO Wave 1B).
 * `page` is indexable on clean hub/catalog/blog URLs; it is not a facet trap.
 */

export const PAGE_QUERY_KEY = "page";

/** Parse `page` query → 1-based page number (invalid → 1). */
export function parsePageParam(raw: string | string[] | undefined): number {
  const token = Array.isArray(raw) ? raw[0] : raw;
  if (token == null || token.trim() === "") return 1;
  if (!/^\d+$/.test(token.trim())) return 1;
  const n = Number(token);
  if (!Number.isFinite(n) || n < 1) return 1;
  return Math.floor(n);
}

export function totalPagesFromCount(totalCount: number, pageSize: number): number {
  if (pageSize <= 0) return 1;
  return Math.max(1, Math.ceil(Math.max(0, totalCount) / pageSize));
}

export function isPageBeyondTotal(page: number, totalCount: number, pageSize: number): boolean {
  if (page <= 1) return false;
  const total = totalPagesFromCount(totalCount, pageSize);
  return page > total;
}

export function catalogListSkip(page: number, pageSize: number): number {
  return (Math.max(1, page) - 1) * pageSize;
}

/** Build pathname + query; omits `page` when page ≤ 1. */
export function buildPaginatedHref(
  pathname: string,
  searchParams: URLSearchParams,
  page: number,
): string {
  const next = new URLSearchParams(searchParams.toString());
  if (page <= 1) next.delete(PAGE_QUERY_KEY);
  else next.set(PAGE_QUERY_KEY, String(page));
  const qs = next.toString();
  return qs ? `${pathname}?${qs}` : pathname;
}

export type CatalogParamPatch = Record<
  string,
  string | number | number[] | string[] | null | undefined
>;

/**
 * Apply catalog filter patch to URLSearchParams.
 * Any filter change clears `page` unless the patch explicitly sets `page`.
 */
export function applyCatalogParamPatch(
  base: URLSearchParams,
  patch: CatalogParamPatch,
): URLSearchParams {
  const next = new URLSearchParams(base.toString());
  const patchTouchesPage = Object.prototype.hasOwnProperty.call(patch, PAGE_QUERY_KEY);
  const filterKeys = Object.keys(patch).filter((k) => k !== PAGE_QUERY_KEY);

  for (const [key, value] of Object.entries(patch)) {
    if (value == null || value === "") {
      next.delete(key);
    } else if (Array.isArray(value)) {
      if (value.length === 0) next.delete(key);
      else next.set(key, value.map(String).join(","));
    } else {
      next.set(key, String(value));
    }
  }

  if ("category" in patch) {
    next.delete("category_id");
    next.delete("category_slug");
    if (patch.category == null || patch.category === "") {
      next.delete("category");
      const toDelete: string[] = [];
      next.forEach((_, key) => {
        if (key.startsWith("spec_")) toDelete.push(key);
      });
      toDelete.forEach((key) => next.delete(key));
    }
  }
  if ("brand" in patch) {
    next.delete("brand_id");
    next.delete("brand_slug");
  }

  if (filterKeys.length > 0 && !patchTouchesPage) {
    next.delete(PAGE_QUERY_KEY);
  }

  return next;
}

/** True when URL should redirect away from `?page=1` (clean canonical). */
export function shouldStripPageOne(searchParams: URLSearchParams): boolean {
  const raw = searchParams.get(PAGE_QUERY_KEY);
  if (raw == null) return false;
  return parsePageParam(raw) === 1;
}

export function stripPageOneParams(searchParams: URLSearchParams): string {
  const next = new URLSearchParams(searchParams.toString());
  next.delete(PAGE_QUERY_KEY);
  return next.toString();
}

export function paginatedTitle(baseTitle: string, page: number): string {
  if (page <= 1) return baseTitle;
  return `${baseTitle} – صفحه ${page}`;
}

export function paginatedCanonicalPath(pathname: string, page: number): string {
  if (page <= 1) return pathname;
  return `${pathname}?${PAGE_QUERY_KEY}=${page}`;
}
