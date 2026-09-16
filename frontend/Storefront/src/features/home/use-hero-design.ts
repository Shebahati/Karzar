"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchHeroDesignPack } from "@/features/home/hero-design";
import type { DesignedHeroPack } from "@/types/hero-design";

export function useDesignedHeroPack(
  initialData?: DesignedHeroPack | null,
  initialDataUpdatedAt?: number,
) {
  const hasInitial = initialData != null;
  return useQuery({
    queryKey: ["hero-design-pack"],
    queryFn: fetchHeroDesignPack,
    staleTime: 30_000,
    retry: false,
    initialData: hasInitial ? initialData : undefined,
    initialDataUpdatedAt: hasInitial ? initialDataUpdatedAt : undefined,
  });
}
