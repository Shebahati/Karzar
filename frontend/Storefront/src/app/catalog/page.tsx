import { Suspense } from "react";
import type { Metadata } from "next";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { CatalogView } from "@/components/catalog/catalog-view";
import { Container } from "@/components/ui/container";
import { ProductCardSkeleton } from "@/components/product/product-card";
import { catalogKeys } from "@/features/catalog/keys";
import { NOINDEX_FOLLOW, isFacetedSearchParams } from "@/lib/crawl-hygiene";
import { getQueryClient } from "@/lib/get-query-client";
import { catalogService } from "@/services/catalog";
import type { CategoryTreeNode } from "@/types/category";

const DEFAULT_PLP = { limit: 24, skip: 0 } as const;

type SearchParams = Record<string, string | string[] | undefined>;

function firstParam(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}): Promise<Metadata> {
  const sp = await searchParams;
  const faceted = isFacetedSearchParams(sp);
  return {
    title: "فروشگاه ابزار",
    description: "مرور و فیلتر محصولات ابزار صنعتی و تراشکاری کارزار.",
    alternates: { canonical: "/catalog" },
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

  const categoryRaw = firstParam(sp.category) ?? firstParam(sp.category_id);
  const categoryId = categoryRaw != null ? Number(categoryRaw) : undefined;
  const plpParams = {
    ...DEFAULT_PLP,
    ...(Number.isFinite(categoryId) && categoryId! > 0
      ? { category_id: categoryId }
      : {}),
  };

  const queryClient = getQueryClient();
  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: catalogKeys.products(plpParams),
      queryFn: () => catalogService.listProducts({ ...plpParams }),
    }),
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

  // Prop seed so carousel SSR matches client even if Provider QueryClient differs.
  const initialTree =
    queryClient.getQueryData<CategoryTreeNode[]>(catalogKeys.categoriesTree()) ?? [];

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <Suspense fallback={<CatalogFallback />}>
        <CatalogView initialTree={initialTree} />
      </Suspense>
    </HydrationBoundary>
  );
}

function CatalogFallback() {
  return (
    <Container className="py-10">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <ProductCardSkeleton key={i} />
        ))}
      </div>
    </Container>
  );
}
