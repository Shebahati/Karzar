"use client";

import { useQuery } from "@tanstack/react-query";
import { orderService } from "@/services/orders";

export const orderKeys = {
  mine: (params: { skip?: number; limit?: number }) => ["orders", "mine", params] as const,
  track: (code: string) => ["orders", "track", code] as const,
};

export function useMyOrders(params: { skip?: number; limit?: number } = {}) {
  return useQuery({
    queryKey: orderKeys.mine(params),
    queryFn: () => orderService.listMine(params),
  });
}

export function useOrderTracking(trackingCode: string, enabled = true) {
  return useQuery({
    queryKey: orderKeys.track(trackingCode),
    queryFn: () => orderService.track(trackingCode),
    enabled: enabled && Boolean(trackingCode),
  });
}
