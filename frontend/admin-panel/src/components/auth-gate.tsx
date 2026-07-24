"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { authService } from "@/services/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { env } from "@/config/env";

/**
 * Client-side route guard. Confirms API session + /auth/me role (super_admin).
 * Signed HttpOnly edge cookie is refreshed on success for middleware UX.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let interval: number | undefined;

    async function verify() {
      try {
        await authService.assertAdminSession();
        if (cancelled) return;
        setDenied(false);
        setReady(true);

        interval = window.setInterval(() => {
          void (async () => {
            try {
              await authService.assertAdminSession();
            } catch {
              const next = encodeURIComponent(pathname);
              void authService.logout();
              router.replace(`/login?next=${next}&expired=1`);
            }
          })();
        }, 60_000);
      } catch {
        if (cancelled) return;
        setDenied(true);
        setReady(false);
        const next = encodeURIComponent(pathname);
        router.replace(
          env.USE_MOCK
            ? `/login?next=${next}`
            : `/login?next=${next}&forbidden=1`,
        );
      }
    }

    void verify();

    return () => {
      cancelled = true;
      if (interval) window.clearInterval(interval);
    };
  }, [pathname, router]);

  if (denied) {
    return null;
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen flex-col gap-4 bg-background p-8">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64 w-full max-w-4xl" />
      </div>
    );
  }

  return <>{children}</>;
}
