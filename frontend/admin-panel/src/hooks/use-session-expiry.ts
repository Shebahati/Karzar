"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { tokenStorage, tryRefreshAccessToken } from "@/lib/api-client";
import { authService } from "@/services/auth";

/** Warns near expiry, tries refresh first; redirects only if refresh fails. */
export function SessionExpiryWatcher() {
  const router = useRouter();
  const refreshingRef = useRef(false);

  useEffect(() => {
    const interval = window.setInterval(() => {
      const expiresAt = tokenStorage.getExpiresAt();
      if (!expiresAt) return;

      const remaining = expiresAt - Date.now();

      const attemptRefresh = async (reason: "near" | "expired") => {
        if (refreshingRef.current) return;
        refreshingRef.current = true;
        try {
          if (reason === "near") {
            toast.info("در حال تمدید نشست", {
              description: "نشست شما در حال تمدید است…",
            });
          }
          const refreshed = await tryRefreshAccessToken();
          if (refreshed) {
            if (reason === "near") {
              toast.success("نشست تمدید شد");
            }
            return;
          }
          authService.logout();
          toast.error("نشست شما منقضی شده است", {
            description: "لطفاً دوباره وارد شوید.",
          });
          router.replace("/login?expired=1");
        } finally {
          refreshingRef.current = false;
        }
      };

      if (remaining <= 0) {
        void attemptRefresh("expired");
        return;
      }

      // Fire once in the ~30s window when remaining crosses under 2 minutes.
      if (remaining <= 2 * 60_000 && remaining > 2 * 60_000 - 30_000) {
        void attemptRefresh("near");
      }
    }, 30_000);

    return () => window.clearInterval(interval);
  }, [router]);

  return null;
}
