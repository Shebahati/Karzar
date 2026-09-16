import type { Metadata } from "next";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { HomeView } from "@/components/home/home-view";
import { NAV_GROUPS, navGroupsFromApi } from "@/config/nav-groups";
import { catalogKeys } from "@/features/catalog/keys";
import { INDEXABLE_STATIC_CANONICALS, selfCanonicalAlternates } from "@/lib/crawl-hygiene";
import { HOME_CATALOG_PRODUCTS_PARAMS } from "@/features/home/home-catalog-params";
import { getQueryClient } from "@/lib/get-query-client";
import { readPublishedHeroDesignPack } from "@/features/home/hero-design-server";
import { catalogService } from "@/services/catalog";
import type { Brand, CategoryTreeNode } from "@/types/category";

export const metadata: Metadata = {
  alternates: selfCanonicalAlternates(INDEXABLE_STATIC_CANONICALS.home),
};

export default async function HomePage() {
  const queryClient = getQueryClient();

  const [, heroDesignRead] = await Promise.all([
    Promise.allSettled([
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
        queryKey: catalogKeys.products(HOME_CATALOG_PRODUCTS_PARAMS),
        queryFn: () => catalogService.listProducts(HOME_CATALOG_PRODUCTS_PARAMS),
      }),
      queryClient.prefetchQuery({
        queryKey: catalogKeys.brands(),
        queryFn: () => catalogService.listBrands(),
      }),
      queryClient.prefetchQuery({
        queryKey: catalogKeys.articles(),
        queryFn: () => catalogService.listArticles(),
      }),
    ]),
    readPublishedHeroDesignPack(),
  ]);
  const initialDesignedHeroPack = heroDesignRead.pack;
  const initialDesignedHeroPackUpdatedAt = heroDesignRead.loadedAtMs ?? undefined;

  // Pass brands/tree as props so BrandStrip / CategoryOrbsGrid SSR markup matches
  // client first paint even when the Provider QueryClient is a separate server instance.
  const initialBrands = queryClient.getQueryData<Brand[]>(catalogKeys.brands()) ?? [];
  const initialCategoryTree =
    queryClient.getQueryData<CategoryTreeNode[]>(catalogKeys.categoriesTree()) ?? [];

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <HomeView
        initialBrands={initialBrands}
        initialCategoryTree={initialCategoryTree}
        initialDesignedHeroPack={initialDesignedHeroPack}
        initialDesignedHeroPackUpdatedAt={initialDesignedHeroPackUpdatedAt}
      />
    </HydrationBoundary>
  );
}
