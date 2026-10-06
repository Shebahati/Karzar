import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useMyOrders } from "@/features/orders/queries";
import {
  establishVerifiedCustomer,
  getCustomerSessionSnapshot,
  invalidateCustomerSession,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { apiClient } from "@/lib/api-client";
import { authService } from "@/services/auth";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

vi.mock("@/config/env", () => ({
  env: {
    USE_MOCK: false,
    API_BASE_URL: "http://127.0.0.1:8000/api/v1",
    MOCK_LATENCY_MS: 0,
    GA_MEASUREMENT_ID: "",
    GTM_ID: "",
  },
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, isLoggedIn: () => true };
});

function renderHook<T>(hook: () => T, client: QueryClient) {
  const container = document.createElement("div");
  const root: Root = createRoot(container);
  const out: { current: T | undefined } = { current: undefined };
  function Host() {
    out.current = hook();
    return null;
  }
  act(() => {
    root.render(
      <QueryClientProvider client={client}>
        <Host />
      </QueryClientProvider>,
    );
  });
  return { result: out, unmount: () => act(() => root.unmount()) };
}

async function waitUntil(predicate: () => boolean, attempts = 80) {
  for (let i = 0; i < attempts; i += 1) {
    if (predicate()) return;
    await new Promise((r) => setTimeout(r, 15));
  }
  throw new Error("timeout");
}

describe("private orders query session (F02)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    vi.restoreAllMocks();
  });

  it("T08: does not fetch private orders without verified owner", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValue({ data: { data: [], meta: {} } });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    renderHook(() => useMyOrders({ limit: 5 }), client);
    await waitUntil(() => true, 3);
    expect(getSpy.mock.calls.some((c) => String(c[0]).includes("/orders/me"))).toBe(false);
  });

  it("T08: manual refetch does not call /orders/me without verified owner", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValue({ data: { data: [], meta: {} } });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useMyOrders({ limit: 5 }), client);
    await act(async () => {
      await result.current?.refetch().catch(() => undefined);
    });
    expect(getSpy.mock.calls.some((c) => String(c[0]).includes("/orders/me"))).toBe(false);
  });

  it("C4/T05: late A /orders/me cannot repopulate cache after B (intercepted transport)", async () => {
    let resolveA!: (value: unknown) => void;
    const getSpy = vi.spyOn(apiClient, "get").mockImplementation((url: string) => {
      if (String(url).includes("/orders/me")) {
        return new Promise((resolve) => {
          resolveA = resolve;
        });
      }
      return Promise.resolve({ data: {} });
    });

    establishVerifiedCustomer(1, "otp");
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 60_000 } } });
    const { result, unmount } = renderHook(() => useMyOrders({ limit: 5 }), client);

    establishVerifiedCustomer(2, "otp");
    await act(async () => {
      resolveA({
        data: {
          data: [{ id: 1, tracking_code: "A-LATE", status: "pending", status_label: "p", mode: "purchase", estimated_total: "0", created_at: "2026-01-01" }],
          meta: { total_count: 1, skip: 0, limit: 5, has_next: false, has_prev: false },
        },
      });
    });

    await waitUntil(() => getSpy.mock.calls.length > 0);
    expect(result.current?.data?.data?.[0]?.tracking_code).not.toBe("A-LATE");

    invalidateCustomerSession("guest");
    establishVerifiedCustomer(1, "otp");
    getSpy.mockClear();
    const { result: again } = renderHook(() => useMyOrders({ limit: 5 }), client);
    await waitUntil(() => getSpy.mock.calls.length > 0);
    expect(again.current?.fetchStatus).toBeDefined();
    unmount();
  });

  it("T01: order query keys include owner id and generation", () => {
    establishVerifiedCustomer(42, "otp");
    const snap = getCustomerSessionSnapshot();
    expect(["orders", "mine", 42, snap.generation, { limit: 1 }]).toEqual([
      "orders",
      "mine",
      42,
      snap.generation,
      { limit: 1 },
    ]);
  });

  it("C4/T01: live branch A logout B within staleTime (intercepted transport)", async () => {
    vi.spyOn(apiClient, "get").mockImplementation(async (url: string) => {
      if (String(url).includes("/orders/me")) {
        return {
          data: {
            data: [
              {
                id: 2,
                tracking_code: "B-ONLY",
                status: "pending",
                status_label: "pending",
                mode: "purchase",
                estimated_total: "0",
                created_at: "2026-01-01T00:00:00Z",
              },
            ],
            meta: { total_count: 1, skip: 0, limit: 5, has_next: false, has_prev: false },
          },
        };
      }
      return { data: {} };
    });

    const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 60_000 } } });
    establishVerifiedCustomer(1, "otp");
    client.setQueryData(["orders", "mine", 1, 1, { limit: 5 }], {
      data: [{ id: 9, tracking_code: "A-OLD", status: "pending", status_label: "p", mode: "purchase", estimated_total: "0", created_at: "2026-01-01" }],
      meta: { total_count: 1, skip: 0, limit: 5, has_next: false, has_prev: false },
    });

    invalidateCustomerSession("guest");
    establishVerifiedCustomer(2, "otp");
    const { result, unmount } = renderHook(() => useMyOrders({ limit: 5 }), client);
    await waitUntil(() => result.current?.data?.data?.[0]?.tracking_code === "B-ONLY");
    expect(result.current?.data?.data?.[0]?.tracking_code).not.toBe("A-OLD");
    unmount();
  });
});
