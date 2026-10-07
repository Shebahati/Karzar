import { afterEach, describe, expect, it, vi } from "vitest";
import {
  lookupProductSlugForMiddleware,
  middlewareCatalogApiBaseUrl,
  PRODUCT_REDIRECT_LOOKUP_TIMEOUT_MS,
} from "@/lib/middleware-product-slug-lookup";

describe("middlewareProductSlugLookup", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("uses NEXT_PUBLIC_API_BASE_URL", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.karzartools.com/api/v1");
    expect(middlewareCatalogApiBaseUrl()).toBe("https://api.karzartools.com/api/v1");
  });

  it("keeps 2000ms lookup timeout constant", () => {
    expect(PRODUCT_REDIRECT_LOOKUP_TIMEOUT_MS).toBe(2000);
  });

  it("returns null when API responds 404", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "false");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 404 })),
    );
    expect(await lookupProductSlugForMiddleware("999")).toBeNull();
  });
});
