import { Suspense } from "react";
import type { Metadata } from "next";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { CatalogView } from "@/components/catalog/catalog-view";
import { Container } from "@/components/ui/container";
import { ProductCardSkeleton } from "@/components/product/product-card";
import { catalogKeys } from "@/features/catalog/keys";
import { getQueryClient } from "@/lib/get-query-client";
import { catalogService } from "@/services/catalog";

export const metadata: Metadata = {
  title: "فروشگاه ابزار",
  description: "مرور و فیلتر محصولات ابزار صنعتی و تراشکاری کارزار.",
};

const DEFAULT_PLP = { limit: 24, skip: 0 } as const;

/** `useSearchParams` requires a Suspense boundary in the App Router. */
export default async function CatalogPage() {
  const queryClient = getQueryClient();
  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: catalogKeys.products(DEFAULT_PLP),
      queryFn: () => catalogService.listProducts({ ...DEFAULT_PLP }),
    }),
    queryClient.prefetchQuery({
      queryKey: catalogKeys.categoriesFlat(),
      queryFn: () => catalogService.listCategoriesFlat(),
    }),
    queryClient.prefetchQuery({
      queryKey: catalogKeys.brands(),
      queryFn: () => catalogService.listBrands(),
    }),
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <Suspense fallback={<CatalogFallback />}>
        <CatalogView />
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
