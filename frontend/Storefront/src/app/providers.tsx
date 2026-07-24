"use client";

import { useEffect, useState, type ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { useMe } from "@/features/auth/queries";
import { isLoggedIn, tokenStorage } from "@/lib/api-client";
import { getQueryClient } from "@/lib/get-query-client";
import { loadFeatureLabels } from "@/lib/feature-labels";

function SessionWatcher() {
  useEffect(() => {
    const interval = window.setInterval(() => {
      if (tokenStorage.isExpired()) {
        tokenStorage.clear();
        window.dispatchEvent(new Event("karzar-auth-change"));
      }
    }, 30_000);
    return () => window.clearInterval(interval);
  }, []);
  return null;
}

function AuthBootstrap() {
  useMe(isLoggedIn());
  return null;
}

function FeatureLabelsBootstrap() {
  useEffect(() => {
    void loadFeatureLabels();
  }, []);
  return null;
}

/**
 * App-wide client providers.
 * QueryClient comes from getQueryClient() so RSC HydrationBoundary can share cache semantics.
 */
export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => getQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <AuthBootstrap />
      <SessionWatcher />
      <FeatureLabelsBootstrap />
      {children}
    </QueryClientProvider>
  );
}
