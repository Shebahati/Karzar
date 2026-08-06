"use client";

import { useQuery } from "@tanstack/react-query";
import {
  defaultHomeLayoutPack,
  normalizeHomeLayoutPack,
  type HomeLayoutPack,
} from "@/types/home-layout";

const PLACEHOLDER_PACK = defaultHomeLayoutPack();

async function fetchHomeLayoutPack(): Promise<HomeLayoutPack> {
  try {
    const res = await fetch("/home-layout.json", { cache: "no-store" });
    if (!res.ok) return defaultHomeLayoutPack();
    return normalizeHomeLayoutPack(await res.json());
  } catch {
    return defaultHomeLayoutPack();
  }
}

export function useHomeLayoutPack() {
  return useQuery({
    queryKey: ["home-layout-pack"],
    queryFn: fetchHomeLayoutPack,
    staleTime: 30_000,
    retry: false,
    placeholderData: PLACEHOLDER_PACK,
  });
}
