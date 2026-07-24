"use client";

import { useQuery } from "@tanstack/react-query";

import { systemService } from "@/services/system";

export const systemKeys = {
  all: ["system"] as const,
  health: () => [...systemKeys.all, "health"] as const,
  ready: () => [...systemKeys.all, "ready"] as const,
};

export function useSystemHealth() {
  return useQuery({
    queryKey: systemKeys.health(),
    queryFn: () => systemService.getHealth(),
    refetchInterval: 60_000,
    retry: 1,
  });
}

export function useSystemReady() {
  return useQuery({
    queryKey: systemKeys.ready(),
    queryFn: () => systemService.getReady(),
    refetchInterval: 60_000,
    retry: 1,
  });
}
