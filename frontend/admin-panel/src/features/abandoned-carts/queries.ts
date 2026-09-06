"use client";

import { useQuery } from "@tanstack/react-query";
import { abandonedCartsService } from "@/services/abandoned-carts";

export function useAbandonedCarts(params: { skip?: number; limit?: number } = {}) {
  return useQuery({
    queryKey: ["abandoned-carts", params],
    queryFn: () => abandonedCartsService.list(params),
  });
}
