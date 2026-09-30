import { parseCountryList, parseIdList } from "@/lib/catalog-url-parse";
import { isApiProductSort } from "@/types/product";
import type { ProductListParams } from "@/types/product";
import { parsePageParam } from "@/lib/pagination-url";

const SPEC_PREFIX = "spec_";

export type CatalogUrlState = {
  page: number;
  params: ProductListParams;
  categorySlug?: string;
  brandSlug?: string;
};

function firstParam(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function numFromSp(
  sp: URLSearchParams,
  key: string,
): number | undefined {
  const v = sp.get(key);
  return v != null && v !== "" && !Number.isNaN(Number(v)) ? Number(v) : undefined;
}

/** Parse catalog PLP query (server + tests). */
export function parseCatalogUrlState(
  searchParams: Record<string, string | string[] | undefined>,
): CatalogUrlState {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams)) {
    const v = firstParam(value);
    if (v != null) sp.set(key, v);
  }

  const page = parsePageParam(searchParams.page);
  const sortRaw = sp.get("sort");
  const spec_filters: Record<string, string> = {};
  sp.forEach((value, key) => {
    if (key.startsWith(SPEC_PREFIX) && value) {
      spec_filters[key.slice(SPEC_PREFIX.length).replace(/__/g, ".")] = value;
    }
  });

  const brand_ids = parseIdList(sp.get("brand") ?? sp.get("brand_id"));
  const countries = parseCountryList(sp.get("country"));

  const params: ProductListParams = {
    category_id: numFromSp(sp, "category") ?? numFromSp(sp, "category_id"),
    brand_ids: brand_ids.length ? brand_ids : undefined,
    search: sp.get("search") ?? undefined,
    countries: countries.length ? countries : undefined,
    min_price: numFromSp(sp, "min_price"),
    max_price: numFromSp(sp, "max_price"),
    in_stock: sp.get("in_stock") === "1" || undefined,
    on_sale: sp.get("on_sale") === "1" || undefined,
    sort: sortRaw && isApiProductSort(sortRaw) ? sortRaw : undefined,
    spec_filters: Object.keys(spec_filters).length ? spec_filters : undefined,
  };

  return {
    page,
    params,
    categorySlug: sp.get("category_slug") ?? undefined,
    brandSlug: sp.get("brand_slug") ?? undefined,
  };
}
