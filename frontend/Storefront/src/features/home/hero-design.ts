import type { DesignedHeroPack } from "@/types/hero-design";

/** Shared validation for published hero-design.json (server + client). */
export function parseDesignedHeroPack(raw: unknown): DesignedHeroPack | null {
  if (!raw || typeof raw !== "object") return null;
  const data = raw as DesignedHeroPack;
  if (data.version !== 1 || !Array.isArray(data.slides) || !data.slides.length) {
    return null;
  }
  return data;
}

export async function fetchHeroDesignPack(): Promise<DesignedHeroPack | null> {
  try {
    const res = await fetch("/hero-design.json", { cache: "no-store" });
    if (!res.ok) return null;
    const json = (await res.json()) as unknown;
    return parseDesignedHeroPack(json);
  } catch {
    return null;
  }
}
