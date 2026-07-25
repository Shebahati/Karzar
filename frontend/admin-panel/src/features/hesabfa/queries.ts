"use client";

import { useQuery } from "@tanstack/react-query";
import { hesabfaService } from "@/services/hesabfa";

export const hesabfaKeys = {
  all: ["hesabfa"] as const,
  status: () => [...hesabfaKeys.all, "status"] as const,
  websiteSales: () => [...hesabfaKeys.all, "website-sales"] as const,
};

export function useHesabfaStatus() {
  return useQuery({
    queryKey: hesabfaKeys.status(),
    queryFn: () => hesabfaService.getStatus(),
    staleTime: 60_000,
  });
}

/** Website paid-sales only — never displays Hesabfa-sourced metrics. */
export function useWebsitePaidSales() {
  return useQuery({
    queryKey: hesabfaKeys.websiteSales(),
    queryFn: () => hesabfaService.getWebsitePaidSales(),
    staleTime: 60_000,
  });
}
