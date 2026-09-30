import { beforeEach, describe, expect, it, vi } from "vitest";
import * as catalogService from "@/services/catalog";
import {
  collectBlogEntries,
  collectBrandEntries,
  collectCategoryEntries,
  fetchPublicProductTotalCount,
} from "../collect";
import { SitemapGenerationError } from "../errors";

describe("sitemap collectors fail closed", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("category API failure throws", async () => {
    vi.spyOn(catalogService.catalogService, "listCategoriesFlat").mockRejectedValue(
      new Error("timeout"),
    );
    await expect(collectCategoryEntries()).rejects.toBeInstanceOf(SitemapGenerationError);
  });

  it("brand API failure throws", async () => {
    vi.spyOn(catalogService.catalogService, "listBrands").mockRejectedValue(
      new Error("5xx"),
    );
    await expect(collectBrandEntries()).rejects.toBeInstanceOf(SitemapGenerationError);
  });

  it("blog API failure throws", async () => {
    vi.spyOn(catalogService.catalogService, "listArticles").mockRejectedValue(
      new Error("network"),
    );
    await expect(collectBlogEntries()).rejects.toBeInstanceOf(SitemapGenerationError);
  });

  it("real empty blog list is not a failure", async () => {
    vi.spyOn(catalogService.catalogService, "listArticles").mockResolvedValue([]);
    const result = await collectBlogEntries();
    expect(result.entryCount).toBe(0);
  });

  it("product count failure throws", async () => {
    vi.spyOn(catalogService.catalogService, "listProducts").mockRejectedValue(
      new Error("down"),
    );
    await expect(fetchPublicProductTotalCount()).rejects.toBeInstanceOf(
      SitemapGenerationError,
    );
  });
});
