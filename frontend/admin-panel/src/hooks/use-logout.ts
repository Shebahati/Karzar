"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { authService } from "@/services/auth";

const LEGACY_TOKEN_KEYS = ["token", "access_token", "karzar.token"];

/**
 * Clears all auth/session state and redirects to the login page.
 * Use this for sidebar logout and any global sign-out action.
 */
export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useCallback(() => {
    void (async () => {
      await authService.logout();

      if (typeof window !== "undefined") {
        for (const key of LEGACY_TOKEN_KEYS) {
          window.localStorage.removeItem(key);
        }
        window.sessionStorage.clear();
      }

      queryClient.clear();
      router.push("/login");
      router.refresh();
    })();
  }, [queryClient, router]);
}
