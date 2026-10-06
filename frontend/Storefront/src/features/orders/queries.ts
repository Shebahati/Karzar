"use client";

import { useSyncExternalStore } from "react";
import { useQuery, type QueryFunctionContext } from "@tanstack/react-query";
import { orderService } from "@/services/orders";
import {
  getCustomerSessionSnapshot,
  getServerCustomerSessionSnapshot,
  isPrivateDataEnabled,
  isSessionOwnerCurrent,
  subscribeCustomerSession,
} from "@/lib/customer-session";

export const orderKeys = {
  mine: (
    ownerId: number | "none",
    sessionGeneration: number,
    params: { skip?: number; limit?: number },
  ) => ["orders", "mine", ownerId, sessionGeneration, params] as const,
  track: (code: string) => ["orders", "track", code] as const,
};

function usePrivateOrderScope(): { ownerId: number | "none"; sessionGeneration: number } {
  const session = useSyncExternalStore(
    subscribeCustomerSession,
    getCustomerSessionSnapshot,
    getServerCustomerSessionSnapshot,
  );
  return {
    ownerId:
      session.phase === "verified" && session.verifiedCustomerId != null
        ? session.verifiedCustomerId
        : "none",
    sessionGeneration: session.generation,
  };
}

export function useMyOrders(params: { skip?: number; limit?: number } = {}) {
  const scope = usePrivateOrderScope();
  const enabled = isPrivateDataEnabled();

  return useQuery({
    queryKey: orderKeys.mine(scope.ownerId, scope.sessionGeneration, params),
    queryFn: async ({ signal }: QueryFunctionContext) => {
      const snap = getCustomerSessionSnapshot();
      if (!isPrivateDataEnabled() || snap.verifiedCustomerId == null) {
        throw new Error("ORDERS_PRIVATE_DISABLED");
      }
      const ownerId = snap.verifiedCustomerId;
      const gen = snap.generation;
      const data = await orderService.listMine(params, signal);
      if (!isSessionOwnerCurrent(gen, ownerId)) {
        throw new Error("ORDERS_STALE_SESSION");
      }
      return data;
    },
    enabled,
    staleTime: 60_000,
    retry: false,
    placeholderData: undefined,
  });
}

export function useOrderTracking(trackingCode: string, enabled = true) {
  return useQuery({
    queryKey: orderKeys.track(trackingCode),
    queryFn: () => orderService.track(trackingCode),
    enabled: enabled && Boolean(trackingCode),
  });
}
