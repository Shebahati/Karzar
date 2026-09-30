import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { CatalogView } from "@/components/catalog/catalog-view";
import { CATALOG_PAGE_SIZE } from "@/config/catalog-page-size";
import { catalogKeys } from "@/features/catalog/keys";
import { parseCatalogUrlState } from "@/lib/catalog-search-params";
import { catalogPlpParams } from "@/lib/catalog-plp";
import {
  INDEXABLE_STATIC_CANONICALS,
  NOINDEX_FOLLOW,
  isFacetedSearchParams,
  selfCanonicalAlternates,
} from "@/lib/crawl-hygiene";
import { getQueryClient } from "@/lib/get-query-client";
import {
  isPageBeyondTotal,
  paginatedCanonicalPath,
  paginatedTitle,
  totalPagesFromCount,
} from "@/lib/pagination-url";
import { redirectIfPageQueryNeedsNormalization } from "@/lib/pagination-request";
import { catalogService } from "@/services/catalog";
import type { CategoryTreeNode } from "@/types/category";

type SearchParams = Record<string, string | string[] | undefined>;

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}): Promise<Metadata> {
  const sp = await searchParams;
  const faceted = isFacetedSearchParams(sp);
  const { page } = parseCatalogUrlState(sp);
  const baseTitle = "فروشگاه";
  const canonicalPath = faceted
    ? INDEXABLE_STATIC_CANONICALS.catalog
    : paginatedCanonicalPath(INDEXABLE_STATIC_CANONICALS.catalog, page);
  return {
    title: faceted ? baseTitle : paginatedTitle(baseTitle, page),
    description: "مرور و فیلتر محصولات ابزار صنعتی و تراشکاری کارزار.",
    alternates: selfCanonicalAlternates(canonicalPath),
    ...(faceted ? { robots: NOINDEX_FOLLOW } : {}),
  };
}

/**
 * Catalog PLP. Filter selections use `/catalog?category=<id>` in place.
 * Indexable hubs stay at `/categories/{slug}` (menus + in-PLP hub link).
 * `useSearchParams` requires a Suspense boundary in the App Router.
 */
export default async function CatalogPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  redirectIfPageQueryNeedsNormalization("/catalog", sp);

  const { page, params } = parseCatalogUrlState(sp);
  const onSale = sp.on_sale === "1" || (Array.isArray(sp.on_sale) && sp.on_sale[0] === "1");
  const plpParams = catalogPlpParams(
    {
      ...params,
      ...(onSale ? { on_sale: true as const } : {}),
    },
    page,
  );

  const productsPage = await catalogService.listProducts(plpParams);
  const totalCount = productsPage.meta.total_count ?? 0;
  const totalPages = totalPagesFromCount(totalCount, CATALOG_PAGE_SIZE);
  if (page > totalPages || isPageBeyondTotal(page, totalCount, CATALOG_PAGE_SIZE)) {
    notFound();
  }
  if (page > 1 && (productsPage.data?.length ?? 0) === 0) {
    notFound();
  }

  const queryClient = getQueryClient();
  queryClient.setQueryData(catalogKeys.products(plpParams), productsPage);

  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: catalogKeys.categoriesFlat(),
      queryFn: () => catalogService.listCategoriesFlat(),
    }),
    queryClient.prefetchQuery({
      queryKey: catalogKeys.categoriesTree(),
      queryFn: () => catalogService.listCategoriesTree(),
    }),
    queryClient.prefetchQuery({
      queryKey: catalogKeys.brands(),
      queryFn: () => catalogService.listBrands(),
    }),
  ]);

  const initialTree =
    queryClient.getQueryData<CategoryTreeNode[]>(catalogKeys.categoriesTree()) ?? [];

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <CatalogView
        serverSearchParams={sp}
        initialTree={initialTree}
        initialProductsSeed={{ params: plpParams, response: productsPage }}
      />
    </HydrationBoundary>
  );
}
