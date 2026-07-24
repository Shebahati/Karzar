"use client";

import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

/**
 * Application-wide client providers.
 *
 * A single QueryClient is created per browser session via `useState` so that
 * it is not re-instantiated on re-renders (which would drop the cache).
 */
export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            gcTime: 5 * 60 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
          mutations: {
            retry: 0,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="bottom-left"
        dir="rtl"
        richColors
        closeButton
        toastOptions={{
          style: { fontFamily: "var(--font-iranyekan)" },
        }}
      />
    </QueryClientProvider>
  );
}
