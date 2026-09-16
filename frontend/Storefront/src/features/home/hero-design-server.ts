import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import { parseDesignedHeroPack } from "@/features/home/hero-design";
import type { DesignedHeroPack } from "@/types/hero-design";

export type PublishedHeroDesignRead = {
  pack: DesignedHeroPack | null;
  loadedAtMs: number | null;
};

/** Read runtime-published hero pack from the Storefront public directory. */
export async function readPublishedHeroDesignPack(): Promise<PublishedHeroDesignRead> {
  const loadedAtMs = Date.now();
  try {
    const filePath = path.join(process.cwd(), "public", "hero-design.json");
    const raw = await fs.readFile(filePath, "utf8");
    const pack = parseDesignedHeroPack(JSON.parse(raw) as unknown);
    return { pack, loadedAtMs: pack ? loadedAtMs : null };
  } catch {
    return { pack: null, loadedAtMs: null };
  }
}
