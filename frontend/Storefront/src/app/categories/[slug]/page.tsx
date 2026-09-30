import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { CategoryHubView } from "@/components/category/category-hub-view";
import { CATALOG_PAGE_SIZE } from "@/config/catalog-page-size";
import { catalogKeys } from "@/features/catalog/keys";
import { catalogPlpParams } from "@/lib/catalog-plp";
import { parseCatalogUrlState } from "@/lib/catalog-search-params";
import {
  NOINDEX_FOLLOW,
  isEmptyCategoryHub,
  isFacetedSearchParams,
} from "@/lib/crawl-hygiene";
import { rejectUnlessEntityNotFound } from "@/lib/entity-lookup";
import { getHubIntro, hubIntroExcerpt } from "@/lib/hub-intros";
import { buildCategoryHubJsonLd } from "@/lib/json-ld";
import { getQueryClient } from "@/lib/get-query-client";
import {
  isPageBeyondTotal,
  paginatedCanonicalPath,
  paginatedTitle,
  parsePageParam,
} from "@/lib/pagination-url";
import { redirectIfPageQueryNeedsNormalization } from "@/lib/pagination-request";
import { catalogService } from "@/services/catalog";
import type { CategoryFlat, CategoryTreeNode } from "@/types/category";

type SearchParams = Record<string, string | string[] | undefined>;

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<SearchParams>;
};

async function resolveCategory(slug: string): Promise<CategoryFlat> {
  return catalogService.getCategoryBySlug(slug);
}

export async function generateMetadata({
  params,
  searchParams,
}: Props): Promise<Metadata> {
  const { slug } = await params;
  const sp = await searchParams;
  const faceted = isFacetedSearchParams(sp, { ignoreCategoryKeys: true });
  let category: CategoryFlat;
  try {
    category = await resolveCategory(slug);
  } catch (error) {
    rejectUnlessEntityNotFound(error);
  }

  // Preserve existing contract: empty hubs are notFound (hard 404), not 200 soft shells.
  if (isEmptyCategoryHub(category.product_count)) {
    notFound();
  }

  const intro = getHubIntro(category.slug ?? slug);
  const page = parsePageParam(sp.page);
  const hubPath = `/categories/${category.slug ?? slug}`;
  const baseTitle = category.meta_title || `${category.name} | کارزار`;
  const title = faceted ? baseTitle : paginatedTitle(baseTitle, page);
  const description =
    category.meta_description ||
    (intro ? hubIntroExcerpt(intro) : null) ||
    `خرید و مشاهده محصولات دسته ${category.name} در فروشگاه ابزار صنعتی کارزار.`;
  const canonicalPath = faceted ? hubPath : paginatedCanonicalPath(hubPath, page);
  return {
    title,
    description,
    alternates: { canonical: canonicalPath },
    openGraph: { title, description, type: "website" },
    ...(faceted ? { robots: NOINDEX_FOLLOW } : {}),
  };
}

function resolveAncestors(
  category: CategoryFlat,
  all: CategoryFlat[],
): CategoryFlat[] {
  const byId = new Map(all.map((c) => [c.id, c]));
  const seen = new Set<number>();
  const out: CategoryFlat[] = [];
  for (const id of category.ancestor_ids ?? []) {
    if (seen.has(id)) continue;
    seen.add(id);
    const node = byId.get(id);
    if (node) out.push(node);
  }
  return out;
}

export default async function CategoryHubPage({ params, searchParams }: Props) {
  const { slug } = await params;
  const sp = await searchParams;
  const hubPath = `/categories/${slug}`;
  redirectIfPageQueryNeedsNormalization(hubPath, sp);

  let category: CategoryFlat;
  try {
    category = await resolveCategory(slug);
  } catch (error) {
    rejectUnlessEntityNotFound(error);
  }

  // Soft-404 → hard 404: empty hubs must not return 200.
  if (isEmptyCategoryHub(category.product_count)) {
    notFound();
  }

  const { page } = parseCatalogUrlState(sp);
  const plpParams = catalogPlpParams({ category_id: category.id }, page);
  const productsPage = await catalogService.listProducts(plpParams);
  if (isPageBeyondTotal(page, productsPage.meta.total_count, CATALOG_PAGE_SIZE)) {
    notFound();
  }

  const intro = getHubIntro(category.slug ?? slug);
  const queryClient = getQueryClient();

  let jsonLd: Record<string, unknown> | null = null;
  try {
    const [all] = await Promise.all([
      queryClient.fetchQuery({
        queryKey: catalogKeys.categoriesFlat(),
        queryFn: () => catalogService.listCategoriesFlat(),
      }),
      queryClient.fetchQuery({
        queryKey: catalogKeys.categoriesTree(),
        queryFn: () => catalogService.listCategoriesTree(),
      }),
    ]);
    queryClient.setQueryData(catalogKeys.products(plpParams), productsPage);
    const categoryForLd =
      !category.meta_description && intro
        ? { ...category, meta_description: hubIntroExcerpt(intro) }
        : category;
    jsonLd = buildCategoryHubJsonLd({
      category: categoryForLd,
      ancestors: resolveAncestors(category, all),
      products: productsPage.data ?? [],
    });
  } catch {
    jsonLd = null;
  }

  const initialFlat =
    queryClient.getQueryData<CategoryFlat[]>(catalogKeys.categoriesFlat()) ?? [];
  const initialTree =
    queryClient.getQueryData<CategoryTreeNode[]>(catalogKeys.categoriesTree()) ?? [];

  return (
    <>
      {jsonLd ? (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      ) : null}
      <HydrationBoundary state={dehydrate(queryClient)}>
        <CategoryHubView
          category={category}
          intro={intro}
          initialTree={initialTree}
          initialFlat={initialFlat}
          initialProductsSeed={{ params: plpParams, response: productsPage }}
          serverSearchParams={sp}
        />
      </HydrationBoundary>
    </>
  );
}
