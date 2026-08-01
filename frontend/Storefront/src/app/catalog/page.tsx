import { Suspense } from "react";
import type { Metadata } from "next";
import { redirect } from "next/navigation";
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
 * Dual-run SEO: when `/catalog?category={id}` points at a category with a slug,
 * permanently redirect to the indexable hub `/categories/{slug}` while preserving
 * other facet query params (brand, specs, etc.).
 */
async function maybeRedirectCategoryIdToHub(searchParams: SearchParams): Promise<void> {
  const raw = firstParam(searchParams.category) ?? firstParam(searchParams.category_id);
  if (!raw) return;
  const categoryId = Number(raw);
  if (!Number.isFinite(categoryId) || categoryId <= 0) return;

  let matchSlug: string | null = null;
  try {
    const categories = await catalogService.listCategoriesFlat();
    matchSlug = categories.find((c) => c.id === categoryId)?.slug ?? null;
  } catch {
    // Keep serving /catalog if category lookup fails.
    return;
  }
  if (!matchSlug) return;

  const next = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams)) {
    if (key === "category" || key === "category_id" || key === "category_slug") continue;
    const v = firstParam(value);
    if (v != null && v !== "") next.set(key, v);
  }
  const qs = next.toString();
  // Must not wrap redirect() in try/catch — Next uses thrown NEXT_REDIRECT.
  redirect(qs ? `/categories/${matchSlug}?${qs}` : `/categories/${matchSlug}`);
}

/** `useSearchParams` requires a Suspense boundary in the App Router. */
export default async function CatalogPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  await maybeRedirectCategoryIdToHub(sp);

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
