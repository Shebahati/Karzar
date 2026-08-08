"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authService } from "@/services/auth";
import { isLoggedIn } from "@/lib/api-client";
import type { MeResponse } from "@/types/auth";

export const authKeys = {
  me: ["auth", "me"] as const,
};

/**
 * Session-aware /me query. Waits until after mount before reading cookies/LS
 * so enablement does not flip mid-hydration (avoids setState-before-mount).
 */
export function useMe(enabled = true) {
  const [sessionReady, setSessionReady] = useState(false);
  useEffect(() => {
    setSessionReady(true);
  }, []);

  const hasSession = sessionReady && isLoggedIn();

  return useQuery({
    queryKey: authKeys.me,
    queryFn: () => authService.getMe(),
    enabled: enabled && hasSession,
    staleTime: 60_000,
    retry: false,
  });
}

export function useUpdateFullName() {
  const queryClient = useQueryClient();
  return useMutation<MeResponse, Error, string>({
    mutationFn: (fullName) => authService.updateFullName(fullName),
    onSuccess: (me) => {
      queryClient.setQueryData(authKeys.me, me);
    },
  });
}
