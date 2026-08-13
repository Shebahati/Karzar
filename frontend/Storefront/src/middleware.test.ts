import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "./middleware";

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
});
