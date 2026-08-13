import type { Metadata } from "next";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { HomeView } from "@/components/home/home-view";
import { NAV_GROUPS, navGroupsFromApi } from "@/config/nav-groups";
import { catalogKeys } from "@/features/catalog/keys";
import { INDEXABLE_STATIC_CANONICALS, selfCanonicalAlternates } from "@/lib/crawl-hygiene";
import { getQueryClient } from "@/lib/get-query-client";
import { catalogService } from "@/services/catalog";
import type { Brand, CategoryTreeNode } from "@/types/category";

export const metadata: Metadata = {
  alternates: selfCanonicalAlternates(INDEXABLE_STATIC_CANONICALS.home),
};

const DISCOUNT_PARAMS = { limit: 12, sort: "newest" as const };
const NEWEST_PARAMS = { limit: 10, sort: "newest" as const };

export default async function HomePage() {
  const queryClient = getQueryClient();

  await Promise.allSettled([
    queryClient.prefetchQuery({
      queryKey: catalogKeys.hero(),
      queryFn: () => catalogService.listHeroSlides(),
    }),
    queryClient.prefetchQuery({
      queryKey: catalogKeys.navGroups(),
      queryFn: async () => {
        const rows = await catalogService.listNavGroups();
        const fromApi = navGroupsFromApi(rows);
        return fromApi.length > 0 ? fromApi : NAV_GROUPS;
      },
    }),
    queryClient.prefetchQuery({
      queryKey: catalogKeys.categoriesTree(),
      queryFn: () => catalogService.listCategoriesTree(),
    }),
    queryClient.prefetchQuery({
      queryKey: catalogKeys.products(DISCOUNT_PARAMS),
      queryFn: () => catalogService.listProducts(DISCOUNT_PARAMS),
    }),
    queryClient.prefetchQuery({
      queryKey: catalogKeys.products(NEWEST_PARAMS),
      queryFn: () => catalogService.listProducts(NEWEST_PARAMS),
    }),
    queryClient.prefetchQuery({
      queryKey: catalogKeys.brands(),
      queryFn: () => catalogService.listBrands(),
    }),
    queryClient.prefetchQuery({
      queryKey: catalogKeys.articles(),
      queryFn: () => catalogService.listArticles(),
    }),
  ]);

  // Pass brands/tree as props so BrandStrip / CategoryOrbsGrid SSR markup matches
  // client first paint even when the Provider QueryClient is a separate server instance.
  const initialBrands = queryClient.getQueryData<Brand[]>(catalogKeys.brands()) ?? [];
  const initialCategoryTree =
    queryClient.getQueryData<CategoryTreeNode[]>(catalogKeys.categoriesTree()) ?? [];

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <HomeView initialBrands={initialBrands} initialCategoryTree={initialCategoryTree} />
    </HydrationBoundary>
  );
}
