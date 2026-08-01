"use client";

import { useQuery } from "@tanstack/react-query";
import type { DesignedHeroPack } from "@/types/hero-design";

async function fetchHeroDesignPack(): Promise<DesignedHeroPack | null> {
  try {
    const res = await fetch("/hero-design.json", { cache: "no-store" });
    if (!res.ok) return null;
    const data = (await res.json()) as DesignedHeroPack;
    if (!data || data.version !== 1 || !Array.isArray(data.slides) || !data.slides.length) {
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

export function useDesignedHeroPack() {
  return useQuery({
    queryKey: ["hero-design-pack"],
    queryFn: fetchHeroDesignPack,
    staleTime: 30_000,
    retry: false,
  });
}
