"use client";

import { useEffect, useState, type ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { useMe } from "@/features/auth/queries";
import { tokenStorage } from "@/lib/api-client";
import { getQueryClient } from "@/lib/get-query-client";
import { loadFeatureLabels } from "@/lib/feature-labels";
import { useAddressStore } from "@/store/address-store";
import { useCartStore } from "@/store/cart-store";

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

/** Prefetch /me only after mount — session reads must not run during hydration render. */
function AuthBootstrap() {
  useMe(true);
  return null;
}

function FeatureLabelsBootstrap() {
  useEffect(() => {
    void loadFeatureLabels();
  }, []);
  return null;
}

/**
 * Zustand persist must not rehydrate during module init / hydration render —
 * localStorage merge is sync-thenable and setStates subscribers before mount.
 */
function PersistRehydrate() {
  useEffect(() => {
    void useCartStore.persist.rehydrate();
    void useAddressStore.persist.rehydrate();
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
      <PersistRehydrate />
      <AuthBootstrap />
      <SessionWatcher />
      <FeatureLabelsBootstrap />
      {children}
    </QueryClientProvider>
  );
}
