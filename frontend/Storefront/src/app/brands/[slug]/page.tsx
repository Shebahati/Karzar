import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { BrandHubView } from "@/components/brand/brand-hub-view";
import { CATALOG_PAGE_SIZE } from "@/config/catalog-page-size";
import { catalogKeys } from "@/features/catalog/keys";
import { catalogPlpParams } from "@/lib/catalog-plp";
import { parseCatalogUrlState } from "@/lib/catalog-search-params";
import { NOINDEX_FOLLOW, isFacetedSearchParams } from "@/lib/crawl-hygiene";
import { rejectUnlessEntityNotFound } from "@/lib/entity-lookup";
import { buildBrandHubJsonLd } from "@/lib/json-ld";
import { getQueryClient } from "@/lib/get-query-client";
import {
  isPageBeyondTotal,
  paginatedCanonicalPath,
  paginatedTitle,
  parsePageParam,
} from "@/lib/pagination-url";
import { redirectIfPageQueryNeedsNormalization } from "@/lib/pagination-request";
import { catalogService } from "@/services/catalog";
import type { Brand } from "@/types/category";

type SearchParams = Record<string, string | string[] | undefined>;

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<SearchParams>;
};

/** D21 Q1=A / Q2=A: below ≥1 active products → still 200, noindex. */
function isThinBrandHub(productCount: number | null | undefined): boolean {
  return (productCount ?? 0) < 1;
}

export async function generateMetadata({
  params,
  searchParams,
}: Props): Promise<Metadata> {
  const { slug } = await params;
  const sp = await searchParams;
  const faceted = isFacetedSearchParams(sp);
  let brand: Brand;
  try {
    brand = await catalogService.getBrandBySlug(slug);
  } catch (error) {
    rejectUnlessEntityNotFound(error);
  }

  const thin = isThinBrandHub(brand.product_count);
  const page = parsePageParam(sp.page);
  const hubPath = `/brands/${brand.slug ?? slug}`;
  const baseTitle = brand.meta_title || `${brand.name} | کارزار`;
  const title = thin || faceted ? baseTitle : paginatedTitle(baseTitle, page);
  const description =
    brand.meta_description ||
    `محصولات برند ${brand.name} در فروشگاه ابزار صنعتی کارزار.`;
  const canonicalPath = thin || faceted ? hubPath : paginatedCanonicalPath(hubPath, page);
  return {
    title,
    description,
    alternates: { canonical: canonicalPath },
    openGraph: { title, description, type: "website" },
    ...(thin || faceted ? { robots: NOINDEX_FOLLOW } : {}),
  };
}

export default async function BrandHubPage({ params, searchParams }: Props) {
  const { slug } = await params;
  const sp = await searchParams;
  const hubPath = `/brands/${slug}`;
  redirectIfPageQueryNeedsNormalization(hubPath, sp);

  let brand: Brand;
  try {
    brand = await catalogService.getBrandBySlug(slug);
  } catch (error) {
    rejectUnlessEntityNotFound(error);
  }

  const { page } = parseCatalogUrlState(sp);
  const plpParams = catalogPlpParams({ brand_ids: [brand.id] }, page);
  const productsPage = await catalogService.listProducts(plpParams);
  if (isPageBeyondTotal(page, productsPage.meta.total_count, CATALOG_PAGE_SIZE)) {
    notFound();
  }

  const queryClient = getQueryClient();
  queryClient.setQueryData(catalogKeys.products(plpParams), productsPage);

  let jsonLd: Record<string, unknown> | null = null;
  try {
    jsonLd = buildBrandHubJsonLd({
      brand,
      products: productsPage.data ?? [],
    });
  } catch {
    jsonLd = null;
  }

  return (
    <>
      {jsonLd ? (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      ) : null}
      <HydrationBoundary state={dehydrate(queryClient)}>
        <BrandHubView
          brand={brand}
          initialProductsSeed={{ params: plpParams, response: productsPage }}
          serverSearchParams={sp}
        />
      </HydrationBoundary>
    </>
  );
}
