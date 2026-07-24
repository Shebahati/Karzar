import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { HomeView } from "@/components/home/home-view";
import { catalogKeys } from "@/features/catalog/keys";
import { getQueryClient } from "@/lib/get-query-client";
import { catalogService } from "@/services/catalog";

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

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <HomeView />
    </HydrationBoundary>
  );
}
