import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-client";
import { isEntityNotFoundError } from "@/lib/entity-lookup";

describe("isEntityNotFoundError", () => {
  it("treats ApiError 404 as not found", () => {
    expect(isEntityNotFoundError(new ApiError(404, { message: "gone" }))).toBe(true);
  });

  it("does not treat ApiError 500 as not found", () => {
    expect(isEntityNotFoundError(new ApiError(500, { message: "boom" }))).toBe(false);
  });

  it("matches mock Persian / English not-found messages", () => {
    expect(isEntityNotFoundError(new Error("محصول یافت نشد."))).toBe(true);
    expect(isEntityNotFoundError(new Error("Category not found"))).toBe(true);
    expect(isEntityNotFoundError(new Error("timeout"))).toBe(false);
  });
});

describe("catalogService blog real-mode integrity", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
    vi.clearAllMocks();
  });

  async function loadCatalogWithApiMock(apiImpl: {
    get: ReturnType<typeof vi.fn>;
  }) {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "false");
    vi.doMock("@/lib/api-client", async () => {
      const actual = await vi.importActual<typeof import("@/lib/api-client")>(
        "@/lib/api-client",
      );
      return {
        ...actual,
        apiClient: {
          get: apiImpl.get,
          post: vi.fn(),
        },
      };
    });
    vi.doMock("@/lib/get-mock-api", () => ({
      getMockApi: vi.fn(async () => {
        throw new Error("mock API must not be used in real mode");
      }),
    }));
    return import("@/services/catalog");
  }

  it("listArticles returns [] when live CMS is empty (no mock)", async () => {
    const get = vi.fn(async () => ({ data: { data: [] } }));
    const { catalogService } = await loadCatalogWithApiMock({ get });
    await expect(catalogService.listArticles()).resolves.toEqual([]);
    expect(get).toHaveBeenCalledWith("/blog/");
  });

  it("listArticles propagates upstream failure (no mock)", async () => {
    const get = vi.fn(async () => {
      throw new ApiError(503, { message: "unavailable" });
    });
    const { catalogService } = await loadCatalogWithApiMock({ get });
    await expect(catalogService.listArticles()).rejects.toBeInstanceOf(ApiError);
  });

  it("getArticle propagates API 404 without mock article", async () => {
    const get = vi.fn(async () => {
      throw new ApiError(404, { message: "Article not found" });
    });
    const { catalogService } = await loadCatalogWithApiMock({ get });
    await expect(catalogService.getArticle("missing-slug")).rejects.toMatchObject({
      status: 404,
    });
  });

  it("getArticle propagates API 500 without mock article", async () => {
    const get = vi.fn(async () => {
      throw new ApiError(500, { message: "server" });
    });
    const { catalogService } = await loadCatalogWithApiMock({ get });
    await expect(catalogService.getArticle("any")).rejects.toMatchObject({
      status: 500,
    });
  });
});

describe("sitemap blog mock contamination", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("emits no blog URLs when listArticles returns empty in real mode", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "false");
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://www.karzartools.com");
    vi.doMock("@/services/catalog", () => ({
      catalogService: {
        listArticles: vi.fn(async () => []),
        listProducts: vi.fn(async () => ({
          data: [],
          meta: { total_count: 0, skip: 0, limit: 1000, has_next: false, has_prev: false },
        })),
        listCategoriesFlat: vi.fn(async () => []),
        listBrands: vi.fn(async () => []),
      },
    }));
    const { collectBlogEntries } = await import("@/lib/sitemap/collect");
    const { entries } = await collectBlogEntries();
    expect(entries.filter((e) => e.loc.includes("/blog/"))).toEqual([]);
  });

  it("fails blog sitemap when listArticles throws in real mode", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "false");
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://www.karzartools.com");
    vi.doMock("@/services/catalog", () => ({
      catalogService: {
        listArticles: vi.fn(async () => {
          throw new ApiError(503, { message: "down" });
        }),
        listProducts: vi.fn(async () => ({
          data: [],
          meta: { total_count: 0, skip: 0, limit: 1000, has_next: false, has_prev: false },
        })),
        listCategoriesFlat: vi.fn(async () => []),
        listBrands: vi.fn(async () => []),
      },
    }));
    const { collectBlogEntries } = await import("@/lib/sitemap/collect");
    const { SitemapGenerationError } = await import("@/lib/sitemap/errors");
    await expect(collectBlogEntries()).rejects.toBeInstanceOf(SitemapGenerationError);
  });
});
