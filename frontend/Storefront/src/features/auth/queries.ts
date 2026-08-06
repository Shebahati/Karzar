"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authService } from "@/services/auth";
import { isLoggedIn } from "@/lib/api-client";
import type { MeResponse } from "@/types/auth";

export const authKeys = {
  me: ["auth", "me"] as const,
};

export function useMe(enabled = true) {
  const hasSession = typeof window !== "undefined" && isLoggedIn();
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
