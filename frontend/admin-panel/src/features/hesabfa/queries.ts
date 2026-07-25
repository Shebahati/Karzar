"use client";

import { useQuery } from "@tanstack/react-query";
import { hesabfaService } from "@/services/hesabfa";

export const hesabfaKeys = {
  all: ["hesabfa"] as const,
  status: () => [...hesabfaKeys.all, "status"] as const,
  salesSummary: () => [...hesabfaKeys.all, "sales-summary"] as const,
};

export function useHesabfaStatus() {
  return useQuery({
    queryKey: hesabfaKeys.status(),
    queryFn: () => hesabfaService.getStatus(),
    staleTime: 60_000,
  });
}

export function useHesabfaSalesSummary() {
  return useQuery({
    queryKey: hesabfaKeys.salesSummary(),
    queryFn: () => hesabfaService.getSalesSummary(),
    staleTime: 60_000,
  });
}
