import { describe, expect, it } from "vitest";
import { parseSitemapLastmod, productLastmod } from "../lastmod";

describe("parseSitemapLastmod", () => {
  it("returns ISO for valid timestamp", () => {
    expect(parseSitemapLastmod("2026-06-01T09:00:00Z")).toMatch(/^2026-06-01T09:00:00/);
  });

  it("omits null/empty/invalid", () => {
    expect(parseSitemapLastmod(null)).toBeUndefined();
    expect(parseSitemapLastmod("")).toBeUndefined();
    expect(parseSitemapLastmod("not-a-date")).toBeUndefined();
  });

  it("product lastmod uses updated_at only", () => {
    expect(productLastmod("2026-01-02T00:00:00Z")).toBeDefined();
    expect(productLastmod(undefined)).toBeUndefined();
  });
});
