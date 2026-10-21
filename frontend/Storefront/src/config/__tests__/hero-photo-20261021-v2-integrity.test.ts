import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import { describe, expect, it } from "vitest";
import manifest from "@/config/hero-photo-20261021-v2-manifest.json";
import { HERO_CALIBRATED_ASSET_DIR } from "@/config/hero-campaign-five";

const publicRoot = path.join(process.cwd(), "public");

/** PR #545 graphic-placeholder pack — must never ship as live hero art again. */
const PLACEHOLDER_PACK_H01_DESKTOP_SHA256 =
  "8da6133fa4d57fe83eff4daab961e5abd79516bbe79092a072b8c66fa9013df8";

function sha256File(absPath: string): string {
  return createHash("sha256").update(readFileSync(absPath)).digest("hex");
}

describe("hero photo-20261021-v2 source integrity", () => {
  it("points campaign art at the v2 photo directory", () => {
    expect(HERO_CALIBRATED_ASSET_DIR).toBe("/images/hero/reborn-5/photo-20261021-v2");
  });

  it("matches Owner-approved MANIFEST.json byte hashes for all ten WebPs", () => {
    expect(manifest.assets).toHaveLength(10);
    for (const asset of manifest.assets) {
      const rel = asset.path_relative_repo.replace(
        /^frontend\/Storefront\/public\//,
        "",
      );
      const abs = path.join(publicRoot, rel);
      const hash = sha256File(abs);
      expect(hash).toBe(asset.sha256);
      expect(hash).not.toBe(PLACEHOLDER_PACK_H01_DESKTOP_SHA256);
    }
  });

  it("rejects the known graphic-placeholder H01 desktop bytes if present on disk", () => {
    const placeholder = path.join(
      publicRoot,
      "images/hero/reborn-5/pack-20261021/H01-special-offers-desktop-16x9.webp",
    );
    try {
      const hash = sha256File(placeholder);
      expect(hash).toBe(PLACEHOLDER_PACK_H01_DESKTOP_SHA256);
    } catch {
      // pack dir optional in some checkouts
    }
    const liveH01 = path.join(
      publicRoot,
      HERO_CALIBRATED_ASSET_DIR.slice(1),
      "H01-special-offers-desktop-16x9.webp",
    );
    expect(sha256File(liveH01)).not.toBe(PLACEHOLDER_PACK_H01_DESKTOP_SHA256);
  });
});
