"use client";

import { useEffect, useState, type ReactNode } from "react";
import { QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import {
  authKeys,
  clearPrivateAuthAndOrderQueries,
  useMe,
} from "@/features/auth/queries";
import {
  CUSTOMER_SESSION_SIGNAL_KEY,
  getCustomerSessionSnapshot,
  invalidateCustomerSession,
  markCustomerSessionChecking,
  notifyExternalSessionHint,
  registerCustomerSessionHandlers,
} from "@/lib/customer-session";
import {
  isLoggedIn,
  tokenStorage,
} from "@/lib/api-client";
import { STOREFRONT_CUSTOMER_KEY } from "@/services/auth";
import { getQueryClient } from "@/lib/get-query-client";
import { loadFeatureLabels } from "@/lib/feature-labels";
import { ADDRESS_PERSIST_KEY, useAddressStore } from "@/store/address-store";
import { useCartStore } from "@/store/cart-store";

function SessionWatcher() {
  useEffect(() => {
    const interval = window.setInterval(() => {
      if (tokenStorage.isExpired()) {
        invalidateCustomerSession("guest");
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

function CustomerSessionBoundary() {
  const queryClient = useQueryClient();

  useEffect(() => {
    registerCustomerSessionHandlers({
      onSessionInvalidated: () => {
        clearPrivateAuthAndOrderQueries(queryClient);
        useAddressStore.getState().clearVisibleAddresses();
        // F03: hide authenticated cart publication; do not mutate server cart.
        useCartStore.getState().hidePublishedCart();
      },
      onSessionVerified: (ownerId, sameOwner) => {
        if (!sameOwner) {
          clearPrivateAuthAndOrderQueries(queryClient);
        }
        // Publish only when stash attribution matches verified owner; foreign/guest stash stays hidden.
        useCartStore.getState().publishStashForVerifiedCustomer(ownerId);
        useAddressStore.getState().hydrateVisibleForVerifiedOwner(ownerId);
      },
    });
  }, [queryClient]);

  useEffect(() => {
    const reverifyFromOtherTab = () => {
      // External storage hint: invalidate/hide locally without rebroadcasting
      // CUSTOMER_SESSION_SIGNAL_KEY (prevents cross-tab signal bounce).
      notifyExternalSessionHint();
      clearPrivateAuthAndOrderQueries(queryClient);
      useAddressStore.getState().clearVisibleAddresses();
      useCartStore.getState().hidePublishedCart();
      if (!isLoggedIn()) {
        invalidateCustomerSession("guest", { broadcast: false });
        return;
      }
      void queryClient.invalidateQueries({ queryKey: authKeys.all });
    };

    const onAuthChange = () => {
      if (!isLoggedIn()) {
        const snap = getCustomerSessionSnapshot();
        if (snap.verifiedCustomerId != null || snap.phase === "checking") {
          invalidateCustomerSession("guest");
        }
        return;
      }
      markCustomerSessionChecking();
      void queryClient.invalidateQueries({ queryKey: authKeys.all });
    };

    const onStorage = (event: StorageEvent) => {
      if (
        event.key === STOREFRONT_CUSTOMER_KEY ||
        event.key === ADDRESS_PERSIST_KEY ||
        event.key === CUSTOMER_SESSION_SIGNAL_KEY
      ) {
        reverifyFromOtherTab();
      }
    };

    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        if (!isLoggedIn()) {
          const snap = getCustomerSessionSnapshot();
          if (snap.verifiedCustomerId != null) {
            invalidateCustomerSession("guest");
          }
          return;
        }
        markCustomerSessionChecking();
        void queryClient.invalidateQueries({ queryKey: authKeys.all });
      }
    };

    window.addEventListener("karzar-auth-change", onAuthChange);
    window.addEventListener("storage", onStorage);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("karzar-auth-change", onAuthChange);
      window.removeEventListener("storage", onStorage);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [queryClient]);

  return null;
}

/**
 * Zustand persist must not rehydrate during module init / hydration render —
 * localStorage merge is sync-thenable and setStates subscribers before mount.
 */
function PersistRehydrate() {
  useEffect(() => {
    void Promise.resolve(useCartStore.persist.rehydrate()).then(() => {
      // Guest stash may republish after mount when token matches; customer stash stays hidden.
      useCartStore.getState().publishStashForCurrentGuestIfMatches();
    });
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
      <CustomerSessionBoundary />
      <AuthBootstrap />
      <SessionWatcher />
      <FeatureLabelsBootstrap />
      {children}
    </QueryClientProvider>
  );
}
