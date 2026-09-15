import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  QueryClient,
  dehydrate,
  hydrate,
} from "@tanstack/react-query";
import { catalogKeys } from "@/features/catalog/keys";
import {
  HOME_CATALOG_PRODUCTS_PARAMS,
  homeCatalogProductsQueryKey,
} from "@/features/home/home-catalog-params";
import { catalogService } from "@/services/catalog";
import type { ProductListResponse } from "@/types/product";

function makeTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        gcTime: 5 * 60 * 1000,
        retry: false,
        refetchOnWindowFocus: false,
      },
    },
  });
}

const mockListResponse: ProductListResponse = {
  data: [
    {
      id: 1,
      name: "Test",
      slug: "test",
      sku: "T-1",
      base_price: "1000",
      stock_status: "موجود",
      availability: true,
      is_original: true,
    },
  ],
  total: 1,
  skip: 0,
  limit: 48,
};

describe("home catalog product data flow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("uses one shared query key for RSC prefetch and client useProducts", () => {
    const fromParams = catalogKeys.products(HOME_CATALOG_PRODUCTS_PARAMS);
    const fromHelper = homeCatalogProductsQueryKey();
    expect(fromHelper).toEqual(fromParams);
    expect(fromHelper).toEqual(["catalog", "products", { limit: 48, sort: "newest" }]);
  });

  it("serves hydrated home products without a second listProducts fetch", async () => {
    const listProducts = vi
      .spyOn(catalogService, "listProducts")
      .mockResolvedValue(mockListResponse);

    const serverClient = makeTestQueryClient();
    await serverClient.prefetchQuery({
      queryKey: homeCatalogProductsQueryKey(),
      queryFn: () => catalogService.listProducts(HOME_CATALOG_PRODUCTS_PARAMS),
    });

    const browserClient = makeTestQueryClient();
    hydrate(browserClient, dehydrate(serverClient));

    await browserClient.fetchQuery({
      queryKey: homeCatalogProductsQueryKey(),
      queryFn: () => catalogService.listProducts(HOME_CATALOG_PRODUCTS_PARAMS),
    });

    expect(listProducts).toHaveBeenCalledTimes(1);
    expect(listProducts).toHaveBeenCalledWith(HOME_CATALOG_PRODUCTS_PARAMS);
  });

  it("documents pre-alignment mismatch: limit 12 prefetch does not satisfy limit 48 client", async () => {
    const listProducts = vi
      .spyOn(catalogService, "listProducts")
      .mockResolvedValue(mockListResponse);

    const serverClient = makeTestQueryClient();
    await serverClient.prefetchQuery({
      queryKey: catalogKeys.products({ limit: 12, sort: "newest" }),
      queryFn: () => catalogService.listProducts({ limit: 12, sort: "newest" }),
    });

    const browserClient = makeTestQueryClient();
    hydrate(browserClient, dehydrate(serverClient));

    await browserClient.fetchQuery({
      queryKey: homeCatalogProductsQueryKey(),
      queryFn: () => catalogService.listProducts(HOME_CATALOG_PRODUCTS_PARAMS),
    });

    expect(listProducts).toHaveBeenCalledTimes(2);
  });
});
