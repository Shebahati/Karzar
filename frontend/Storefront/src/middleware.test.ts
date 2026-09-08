import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "./middleware";

/** Request headers forwarded by `NextResponse.next({ request: { headers } })`. */
function middlewareRequestHeader(
  res: Response,
  name: string,
): string | null {
  return res.headers.get(`x-middleware-request-${name.toLowerCase()}`);
}

function scriptSrcDirective(csp: string): string {
  return csp.match(/script-src ([^;]+)/)?.[1] ?? "";
}

describe("numeric product HTTP 301 (middleware)", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("issues 301 to an encode-once slug Location", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "false");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.karzartools.com/api/v1");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ slug: "مدل-ast-cor305p" }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const res = await middleware(
      new NextRequest("https://www.karzartools.com/product/6587"),
    );

    expect(res.status).toBe(301);
    expect(res.headers.get("location")).toBe(
      `https://www.karzartools.com/product/${encodeURIComponent("مدل-ast-cor305p")}`,
    );
    expect(res.headers.get("content-security-policy")).toContain("'strict-dynamic'");
    expect(middlewareRequestHeader(res, "content-security-policy")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.karzartools.com/api/v1/products/6587",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("does not look up or redirect slug PDPs", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "false");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const res = await middleware(
      new NextRequest(
        `https://www.karzartools.com/product/${encodeURIComponent("مدل-ast-cor305p")}`,
      ),
    );

    expect(res.status).toBeLessThan(300);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("falls through when the product has no slug", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "false");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({ slug: null }),
      })),
    );

    const res = await middleware(
      new NextRequest("https://www.karzartools.com/product/6587"),
    );
    expect(res.status).toBeLessThan(300);
  });

  it("passes through canonical category hub paths", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "true");
    const res = await middleware(
      new NextRequest("https://www.karzartools.com/categories/andaze-daghigh"),
    );
    expect(res.status).toBeLessThan(300);
  });
});

describe("CSP nonce request/response propagation", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("forwards matching nonce CSP on pass-through request and response", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "true");
    const res = await middleware(
      new NextRequest("https://www.karzartools.com/"),
    );

    expect(res.status).toBeLessThan(300);

    const nonce = middlewareRequestHeader(res, "x-nonce");
    const requestCsp = middlewareRequestHeader(res, "content-security-policy");
    const responseCsp = res.headers.get("content-security-policy");

    expect(nonce).toBeTruthy();
    expect(requestCsp).toBeTruthy();
    expect(responseCsp).toBeTruthy();
    expect(requestCsp).toBe(responseCsp);
    expect(requestCsp).toContain(`'nonce-${nonce}'`);
    expect(requestCsp).toContain("'self'");
    expect(requestCsp).toContain("'strict-dynamic'");
    expect(requestCsp).toContain("https://www.googletagmanager.com");
    expect(requestCsp).toContain("https://www.google-analytics.com");
    expect(requestCsp).toContain("https://*.google-analytics.com");
    expect(requestCsp).toContain("https://*.analytics.google.com");
    expect(requestCsp).toContain("https://region1.google-analytics.com");
    expect(res.headers.get("x-frame-options")).toBe("DENY");
    expect(res.headers.get("x-content-type-options")).toBe("nosniff");
  });

  it("keeps request and response CSP identical on slug PDP pass-through", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "false");
    vi.stubGlobal("fetch", vi.fn());

    const res = await middleware(
      new NextRequest(
        `https://www.karzartools.com/product/${encodeURIComponent("مدل-ast-cor305p")}`,
      ),
    );

    expect(res.status).toBeLessThan(300);
    expect(middlewareRequestHeader(res, "content-security-policy")).toBe(
      res.headers.get("content-security-policy"),
    );
  });

  it("does not weaken production script-src", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "true");
    vi.resetModules();
    const { middleware: productionMiddleware } = await import("./middleware");

    const res = await productionMiddleware(
      new NextRequest("https://www.karzartools.com/"),
    );

    const nonce = middlewareRequestHeader(res, "x-nonce");
    const requestCsp = middlewareRequestHeader(res, "content-security-policy");
    const responseCsp = res.headers.get("content-security-policy");
    const scriptSrc = scriptSrcDirective(requestCsp ?? "");

    expect(requestCsp).toBe(responseCsp);
    expect(scriptSrc).toContain("'self'");
    expect(scriptSrc).toContain(`'nonce-${nonce}'`);
    expect(scriptSrc).toContain("'strict-dynamic'");
    expect(scriptSrc).toContain("https://www.googletagmanager.com");
    expect(scriptSrc.split(/\s+/)).not.toContain("*");
    expect(scriptSrc).not.toContain("'unsafe-inline'");
    expect(scriptSrc).not.toContain("'unsafe-eval'");
  });
});

describe("category slug HTTP 301 (middleware)", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.doUnmock("@/lib/category-slug-redirect");
    vi.resetModules();
  });

  it("issues 301 to the canonical category hub and keeps query string", async () => {
    vi.resetModules();
    vi.doMock("@/lib/category-slug-redirect", () => ({
      categoryHubPath: (slug: string) => `/categories/${encodeURIComponent(slug)}`,
      resolveCategorySlugRedirect: (slug: string) =>
        slug === "old-cat" ? "new-cat" : null,
    }));
    const { middleware: categoryMiddleware } = await import("./middleware");
    const res = await categoryMiddleware(
      new NextRequest("https://www.karzartools.com/categories/old-cat?q=1"),
    );

    expect(res.status).toBe(301);
    expect(res.headers.get("location")).toBe(
      "https://www.karzartools.com/categories/new-cat?q=1",
    );
    expect(res.headers.get("content-security-policy")).toContain("'strict-dynamic'");
    expect(middlewareRequestHeader(res, "content-security-policy")).toBeNull();
  });
});
