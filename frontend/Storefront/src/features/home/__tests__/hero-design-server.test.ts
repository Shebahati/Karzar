import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { parseDesignedHeroPack } from "@/features/home/hero-design";
import {
  fetchHeroDesignPackFromApi,
  readPublishedHeroDesignPack,
  resetHeroDesignApiCacheForTests,
} from "@/features/home/hero-design-server";

const publishedPath = path.join(process.cwd(), "public", "hero-design.json");

describe("hero-design-server", () => {
  const fetchMock = vi.fn();
  const previousApiRead = process.env.HERO_STOREFRONT_API_READ;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    delete process.env.HERO_STOREFRONT_API_READ;
    resetHeroDesignApiCacheForTests();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    if (previousApiRead === undefined) {
      delete process.env.HERO_STOREFRONT_API_READ;
    } else {
      process.env.HERO_STOREFRONT_API_READ = previousApiRead;
    }
  });

  it("readPublishedHeroDesignPack uses file only when HERO_STOREFRONT_API_READ is off", async () => {
    const onDisk = parseDesignedHeroPack(
      JSON.parse(readFileSync(publishedPath, "utf8")) as unknown,
    );

    const result = await readPublishedHeroDesignPack();

    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.pack?.slides.length).toBe(onDisk?.slides.length);
    expect(result.loadedAtMs).not.toBeNull();
  });


  it("fetchHeroDesignPackFromApi parses revision-aware payload", async () => {
    const packBody = JSON.parse(readFileSync(publishedPath, "utf8")) as unknown;
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          revision_id: "00000000-0000-4000-8000-000000000001",
          etag: "abc123",
          pack: packBody,
        }),
        {
          status: 200,
          headers: { ETag: '"abc123"' },
        },
      ),
    );

    const api = await fetchHeroDesignPackFromApi(
      "http://127.0.0.1:8000/api/v1",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/storefront/hero-design",
      expect.objectContaining({ next: { revalidate: 60 } }),
    );
    expect(api.ok).toBe(true);
    expect(api.revisionId).toBe("00000000-0000-4000-8000-000000000001");
    expect(api.etag).toBe("abc123");
    expect(api.pack?.slides.length).toBeGreaterThan(0);
  });

  it("readPublishedHeroDesignPack does not fall back to static file on 304 without verified cache", async () => {
    process.env.HERO_STOREFRONT_API_READ = "1";
    fetchMock.mockResolvedValueOnce(
      new Response(null, { status: 304, headers: { ETag: '"etag-unknown"' } }),
    );

    const result = await readPublishedHeroDesignPack();

    expect(result.pack).toBeNull();
    expect(result.loadedAtMs).toBeNull();
  });
});
