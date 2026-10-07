import { afterEach, describe, expect, it, vi } from "vitest";
import {
  lookupProductSlugForMiddleware,
  middlewareCatalogApiBaseUrl,
} from "@/lib/middleware-product-slug-lookup";

describe("middlewareProductSlugLookup", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("uses STOREFRONT_SERVER_API_BASE_URL when set", () => {
    vi.stubEnv("STOREFRONT_SERVER_API_BASE_URL", "http://127.0.0.1:8000/api/v1");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com/api/v1");
    expect(middlewareCatalogApiBaseUrl()).toBe("http://127.0.0.1:8000/api/v1");
  });

  it("retries once on upstream 503", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "false");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503 })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ slug: "retry-slug" }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const slug = await lookupProductSlugForMiddleware("1");
    expect(slug).toBe("retry-slug");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
