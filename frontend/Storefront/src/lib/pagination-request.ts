import { redirect } from "next/navigation";
import {
  PAGE_QUERY_KEY,
  shouldStripPageOne,
  stripPageOneParams,
} from "@/lib/pagination-url";

type SearchParams = Record<string, string | string[] | undefined>;

export function searchParamsToUrlSearchParams(sp: SearchParams): URLSearchParams {
  const next = new URLSearchParams();
  for (const [key, value] of Object.entries(sp)) {
    const token = Array.isArray(value) ? value[0] : value;
    if (token != null && String(token).trim() !== "") {
      next.set(key, String(token));
    }
  }
  return next;
}

/** Redirect when `page` is invalid, empty, or canonical page 1 (`?page=1`). */
export function redirectIfPageQueryNeedsNormalization(
  pathname: string,
  searchParams: SearchParams,
): void {
  const sp = searchParamsToUrlSearchParams(searchParams);
  const raw = sp.get(PAGE_QUERY_KEY);
  if (raw != null) {
    const trimmed = raw.trim();
    const invalid =
      trimmed === "" ||
      !/^\d+$/.test(trimmed) ||
      !Number.isFinite(Number(trimmed)) ||
      Number(trimmed) < 1;
    if (invalid) {
      sp.delete(PAGE_QUERY_KEY);
      const qs = sp.toString();
      redirect(qs ? `${pathname}?${qs}` : pathname);
    }
  }
  if (shouldStripPageOne(sp)) {
    const qs = stripPageOneParams(sp);
    redirect(qs ? `${pathname}?${qs}` : pathname);
  }
}
