/**
 * Server-only product slug lookup for middleware numeric→slug HTTP 301 (RFC-004).
 */
import { catalogProductByIdUrl } from "@/lib/product-url";

export const PRODUCT_REDIRECT_LOOKUP_TIMEOUT_MS = 4000;
export const PRODUCT_REDIRECT_LOOKUP_RETRIES = 1;

function isMockMode(): boolean {
  const flag = process.env.NEXT_PUBLIC_USE_MOCK?.trim().toLowerCase();
  return flag === "true" || flag === "1" || flag === "yes";
}

/** Prefer loopback/server origin in production middleware; fall back to public API base. */
export function middlewareCatalogApiBaseUrl(): string {
  const server =
    process.env.STOREFRONT_SERVER_API_BASE_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return server || "http://localhost:8000/api/v1";
}

function mockProductSlugFromSku(sku: string, id: number): string {
  return (
    sku.toLowerCase().replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") ||
    `product-${id}`
  );
}

async function fetchSlugFromApi(id: string, attempt: number): Promise<string | null> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), PRODUCT_REDIRECT_LOOKUP_TIMEOUT_MS);
  try {
    const res = await fetch(catalogProductByIdUrl(middlewareCatalogApiBaseUrl(), id), {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: ctrl.signal,
      cache: "no-store",
    });
    if (res.status === 404) return null;
    if (!res.ok) {
      if (attempt < PRODUCT_REDIRECT_LOOKUP_RETRIES && res.status >= 500) {
        return fetchSlugFromApi(id, attempt + 1);
      }
      return null;
    }
    const data = (await res.json()) as { slug?: string | null };
    const slug = data.slug?.trim();
    return slug ? slug : null;
  } catch {
    if (attempt < PRODUCT_REDIRECT_LOOKUP_RETRIES) {
      return fetchSlugFromApi(id, attempt + 1);
    }
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Returns canonical slug for numeric id, or null if product missing / no slug / lookup failed.
 */
export async function lookupProductSlugForMiddleware(id: string): Promise<string | null> {
  if (isMockMode()) {
    try {
      const { PRODUCTS } = await import("@/data/mock-data");
      const productId = Number(id);
      const product = PRODUCTS.find((p) => p.id === productId);
      if (!product) return null;
      return mockProductSlugFromSku(product.sku, product.id);
    } catch {
      return null;
    }
  }
  return fetchSlugFromApi(id, 0);
}
