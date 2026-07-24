"use client";

import { useQuery } from "@tanstack/react-query";
import { authService } from "@/services/auth";
import { isLoggedIn } from "@/lib/api-client";

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
