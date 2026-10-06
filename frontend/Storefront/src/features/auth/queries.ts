"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { authService } from "@/services/auth";
import { isLoggedIn } from "@/lib/api-client";
import {
  establishVerifiedCustomer,
  getCustomerSessionSnapshot,
  getPrivateQueryScope,
  getServerCustomerSessionSnapshot,
  isCustomerSessionFenceCurrent,
  isPrivateDataEnabled,
  markCustomerSessionChecking,
  subscribeCustomerSession,
  captureVerifiedCustomerSessionFence,
  type CustomerSessionFence,
  type CustomerSessionSnapshot,
} from "@/lib/customer-session";
import type { MeResponse } from "@/types/auth";

export const authKeys = {
  all: ["auth", "me"] as const,
  me: (scope: ReturnType<typeof getPrivateQueryScope>) =>
    ["auth", "me", ...scope] as const,
};

export function useCustomerSessionSnapshot(): CustomerSessionSnapshot {
  return useSyncExternalStore(
    subscribeCustomerSession,
    getCustomerSessionSnapshot,
    getServerCustomerSessionSnapshot,
  );
}

export function clearPrivateAuthAndOrderQueries(queryClient: QueryClient): void {
  void queryClient.cancelQueries({ queryKey: ["auth", "me"] });
  void queryClient.cancelQueries({ queryKey: ["orders", "mine"] });
  queryClient.removeQueries({ queryKey: ["auth", "me"], exact: false });
  queryClient.removeQueries({ queryKey: ["orders", "mine"], exact: false });
}

/**
 * Session-aware /me query. Waits until after mount before reading cookies/LS
 * so enablement does not flip mid-hydration (avoids setState-before-mount).
 */
export function useMe(enabled = true) {
  const [sessionReady, setSessionReady] = useState(false);
  const session = useCustomerSessionSnapshot();

  useEffect(() => {
    setSessionReady(true);
  }, []);

  const hasSession = sessionReady && isLoggedIn();
  const scope =
    session.phase === "verified" && session.verifiedCustomerId != null
      ? ([session.verifiedCustomerId, session.generation] as const)
      : (["none", session.generation] as const);
  const queryEnabled = enabled && hasSession;

  useEffect(() => {
    if (queryEnabled && !isPrivateDataEnabled() && session.phase === "unknown") {
      markCustomerSessionChecking();
    }
  }, [queryEnabled, session.phase]);

  return useQuery({
    queryKey: authKeys.me(scope),
    queryFn: async ({ signal }) => {
      const startGen = getCustomerSessionSnapshot().generation;
      const me = await authService.getMe({ signal });
      const mid = getCustomerSessionSnapshot();
      // Soft owner retained during "checking" (external hint) must not block
      // authoritative /me when the server reports a different customer.
      if (
        mid.phase === "verified" &&
        mid.verifiedCustomerId != null &&
        mid.verifiedCustomerId !== me.id
      ) {
        throw new Error("ME_STALE_SESSION");
      }
      if (mid.generation !== startGen && mid.verifiedCustomerId !== me.id) {
        throw new Error("ME_STALE_SESSION");
      }
      establishVerifiedCustomer(me.id, "me");
      const after = getCustomerSessionSnapshot();
      if (after.verifiedCustomerId !== me.id || after.phase !== "verified") {
        throw new Error("ME_STALE_SESSION");
      }
      return me;
    },
    enabled: queryEnabled,
    staleTime: 60_000,
    retry: false,
    placeholderData: undefined,
  });
}

export function useUpdateFullName() {
  const queryClient = useQueryClient();
  return useMutation<MeResponse, Error, string, { fence: CustomerSessionFence | null }>({
    mutationFn: (fullName) => authService.updateFullName(fullName),
    onMutate: () => ({ fence: captureVerifiedCustomerSessionFence() }),
    onSuccess: (me, _vars, ctx) => {
      const fence = ctx?.fence ?? null;
      // null verifiedCustomerId (guest/checking) is NOT permission to establish.
      if (!isCustomerSessionFenceCurrent(fence) || fence == null || me.id !== fence.ownerId) {
        return;
      }
      establishVerifiedCustomer(me.id, "profile");
      queryClient.setQueryData(authKeys.me(getPrivateQueryScope()), me);
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation<
    MeResponse,
    Error,
    { full_name: string; company_name?: string | null },
    { fence: CustomerSessionFence | null }
  >({
    mutationFn: (payload) => authService.updateProfile(payload),
    onMutate: () => ({ fence: captureVerifiedCustomerSessionFence() }),
    onSuccess: (me, _vars, ctx) => {
      const fence = ctx?.fence ?? null;
      // null verifiedCustomerId (guest/checking) is NOT permission to establish.
      if (!isCustomerSessionFenceCurrent(fence) || fence == null || me.id !== fence.ownerId) {
        return;
      }
      establishVerifiedCustomer(me.id, "profile");
      queryClient.setQueryData(authKeys.me(getPrivateQueryScope()), me);
    },
  });
}
