import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useMyOrders, orderKeys } from "@/features/orders/queries";
import {
  establishVerifiedCustomer,
  getCustomerSessionSnapshot,
  invalidateCustomerSession,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { orderService } from "@/services/orders";

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
  return { result: out };
}

async function waitUntil(predicate: () => boolean, attempts = 40) {
  for (let i = 0; i < attempts; i += 1) {
    if (predicate()) return;
    await new Promise((r) => setTimeout(r, 10));
  }
  throw new Error("timeout");
}

describe("private orders query session (F02)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    vi.restoreAllMocks();
  });

  it("T08: does not fetch private orders without verified owner", async () => {
    const listSpy = vi.spyOn(orderService, "listMine").mockResolvedValue({
      data: [],
      meta: { total_count: 0, skip: 0, limit: 5, has_next: false, has_prev: false },
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    renderHook(() => useMyOrders({ limit: 5 }), client);
    await waitUntil(() => listSpy.mock.calls.length === 0, 5);
    expect(listSpy).not.toHaveBeenCalled();
  });

  it("T05: late A orders response cannot stick after switch to B", async () => {
    let resolveA!: (value: import("@/types/order").OrderListResponse) => void;
    const listSpy = vi.spyOn(orderService, "listMine").mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveA = resolve;
        }),
    );

    establishVerifiedCustomer(1, "otp");
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useMyOrders({ limit: 5 }), client);

    establishVerifiedCustomer(2, "otp");
    resolveA({
      data: [],
      meta: { total_count: 0, skip: 0, limit: 5, has_next: false, has_prev: false },
    });

    await waitUntil(() => listSpy.mock.calls.length > 0);
    expect(result.current?.data).toBeUndefined();
    const scope = getCustomerSessionSnapshot();
    const cached = client.getQueryData(
      orderKeys.mine(scope.verifiedCustomerId ?? "none", scope.generation, { limit: 5 }),
    );
    expect(cached).toBeUndefined();
  });

  it("T01: order query keys include owner id and generation", () => {
    establishVerifiedCustomer(42, "otp");
    const snap = getCustomerSessionSnapshot();
    expect(orderKeys.mine(42, snap.generation, { limit: 1 })).toEqual([
      "orders",
      "mine",
      42,
      snap.generation,
      { limit: 1 },
    ]);
  });

  it("T07: invalidate clears enabled gate", () => {
    establishVerifiedCustomer(3, "otp");
    invalidateCustomerSession("guest");
    const listSpy = vi.spyOn(orderService, "listMine");
    const client = new QueryClient();
    renderHook(() => useMyOrders(), client);
    expect(listSpy).not.toHaveBeenCalled();
  });
});
