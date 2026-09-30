import { afterEach, describe, expect, it, vi } from "vitest";
import { DISCOUNTS_CATALOG_HREF } from "@/config/l1-categories";
import {
  HOME_CATALOG_PRODUCTS_PARAMS,
  HOME_DEALS_PRODUCTS_PARAMS,
  homeDealsProductsQueryKey,
} from "@/features/home/home-catalog-params";
import { catalogKeys } from "@/features/catalog/keys";
import { API_PRODUCT_SORTS, isApiProductSort } from "@/types/product";

describe("discount discovery FE contract", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("keeps public discounts URL as /catalog?on_sale=1", () => {
    expect(DISCOUNTS_CATALOG_HREF).toBe("/catalog?on_sale=1");
    const sp = new URLSearchParams(DISCOUNTS_CATALOG_HREF.split("?")[1]);
    expect(sp.get("on_sale")).toBe("1");
  });

  it("includes discount_desc and stock_first in API sort allowlist", () => {
    expect(API_PRODUCT_SORTS).toContain("discount_desc");
    expect(API_PRODUCT_SORTS).toContain("stock_first");
    expect(isApiProductSort("discount_desc")).toBe(true);
    expect(isApiProductSort("stock_first")).toBe(true);
  });

  it("home deals query is a dedicated on_sale request", () => {
    expect(HOME_DEALS_PRODUCTS_PARAMS).toEqual({
      on_sale: true,
      in_stock: true,
      sort: "discount_desc",
      limit: 12,
    });
    expect(HOME_CATALOG_PRODUCTS_PARAMS.on_sale).toBeUndefined();
    expect(homeDealsProductsQueryKey()).toEqual(
      catalogKeys.products(HOME_DEALS_PRODUCTS_PARAMS),
    );
  });

  it("catalogService sends live on_sale=true without client-side pagination", async () => {
    const get = vi.fn().mockResolvedValue({
      data: {
        data: [
          {
            id: 9,
            sku: "SALE-1",
            name: "Sale",
            slug: "sale",
            base_price: "900",
            original_price: "1000",
            discount_percent: 10,
          },
        ],
        meta: {
          total_count: 385,
          skip: 0,
          limit: 20,
          has_next: true,
          has_prev: false,
        },
      },
    });

    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "false");
    vi.doMock("@/lib/api-client", async () => {
      const actual = await vi.importActual<typeof import("@/lib/api-client")>(
        "@/lib/api-client",
      );
      return {
        ...actual,
        apiClient: { get, post: vi.fn() },
      };
    });
    vi.doMock("@/lib/get-mock-api", () => ({
      getMockApi: vi.fn(async () => {
        throw new Error("mock must not run");
      }),
    }));

    const { catalogService } = await import("@/services/catalog");
    const result = await catalogService.listProducts({
      on_sale: true,
      skip: 20,
      limit: 20,
    });

    expect(get).toHaveBeenCalledTimes(1);
    const url = String(get.mock.calls[0][0]);
    expect(url).toContain("on_sale=true");
    expect(url).toContain("skip=20");
    expect(url).toContain("limit=20");
    // No over-fetch multiplier (limit*8).
    expect(url).not.toContain("limit=160");
    expect(result.meta.total_count).toBe(385);
    expect(result.data).toHaveLength(1);
  });
});
