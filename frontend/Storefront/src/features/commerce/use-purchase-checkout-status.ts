"use client";

import { useQuery } from "@tanstack/react-query";
import { commerceService } from "@/services/commerce";

export function usePurchaseCheckoutStatus(enabled = true) {
  return useQuery({
    queryKey: ["commerce", "purchase-status"],
    queryFn: () => commerceService.purchaseStatus(),
    enabled,
    staleTime: 15_000,
  });
}
