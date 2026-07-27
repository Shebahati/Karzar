import { afterEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_SITE_URL, getSiteUrl, isSeoIndexable } from "@/lib/site-url";

describe("getSiteUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("defaults to production www", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "");
    expect(getSiteUrl()).toBe(DEFAULT_SITE_URL);
  });

  it("normalizes env origin and strips path", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://www.karzartools.com/shop/");
    expect(getSiteUrl()).toBe("https://www.karzartools.com");
  });

  it("accepts host without scheme", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "preview.example.com");
    expect(getSiteUrl()).toBe("https://preview.example.com");
  });
});

describe("isSeoIndexable", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("defaults to indexable (live VPS topology)", () => {
    vi.stubEnv("NEXT_PUBLIC_SEO_INDEXABLE", "");
    expect(isSeoIndexable()).toBe(true);
  });

  it("honors explicit false for preview hosts", () => {
    vi.stubEnv("NEXT_PUBLIC_SEO_INDEXABLE", "false");
    expect(isSeoIndexable()).toBe(false);
  });
});
