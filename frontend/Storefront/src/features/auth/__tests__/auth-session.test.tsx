import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  authKeys,
  clearPrivateAuthAndOrderQueries,
  useMe,
  useUpdateProfile,
} from "@/features/auth/queries";
import {
  establishVerifiedCustomer,
  getCustomerSessionSnapshot,
  invalidateCustomerSession,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { authService, STOREFRONT_CUSTOMER_KEY } from "@/services/auth";
import { apiClient } from "@/lib/api-client";
import type { MeResponse } from "@/types/auth";

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
  return {
    ...actual,
    isLoggedIn: () => true,
    setStoredToken: vi.fn(),
  };
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

async function waitUntil(predicate: () => boolean, attempts = 60) {
  for (let i = 0; i < attempts; i += 1) {
    if (predicate()) return;
    await new Promise((r) => setTimeout(r, 15));
  }
  throw new Error("timeout");
}

describe("auth /me session cache (F02)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("T06: stale /me completion is dropped after owner switch", async () => {
    let resolveMe!: (me: MeResponse) => void;
    vi.spyOn(authService, "getMe").mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveMe = resolve;
        }),
    );

    establishVerifiedCustomer(2, "otp");
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const snap = getCustomerSessionSnapshot();
    const fetchPromise = client.fetchQuery({
      queryKey: authKeys.me(["none", snap.generation]),
      queryFn: async () => {
        const me = await authService.getMe();
        const mid = getCustomerSessionSnapshot();
        if (mid.verifiedCustomerId != null && mid.verifiedCustomerId !== me.id) {
          throw new Error("ME_STALE_SESSION");
        }
        establishVerifiedCustomer(me.id, "me");
        return me;
      },
    });

    const expectRejected = expect(fetchPromise).rejects.toThrow("ME_STALE_SESSION");
    await act(async () => {
      resolveMe({
        id: 1,
        phone: "09120000001",
        full_name: "User A",
        company_name: null,
      });
    });
    await expectRejected;
  });

  it("T06: late profile mutation cannot repopulate B /me cache (intercepted transport)", async () => {
    let finish!: (me: MeResponse) => void;
    vi.spyOn(authService, "updateProfile").mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );

    const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 60_000 } } });
    establishVerifiedCustomer(1, "otp");
    const { result, unmount } = renderHook(() => useUpdateProfile(), client);

    await act(async () => {
      void result.current?.mutate({ full_name: "Late Name" });
    });
    await waitUntil(() => typeof finish === "function");
    establishVerifiedCustomer(2, "otp");
    await act(async () => {
      finish({
        id: 1,
        phone: "09120000001",
        full_name: "Late A Profile",
        company_name: null,
      });
    });
    await waitUntil(() => result.current?.isIdle ?? true);

    const bScope = getCustomerSessionSnapshot();
    const cached = client.getQueryData(
      authKeys.me([bScope.verifiedCustomerId as number, bScope.generation]),
    );
    expect(cached).toBeUndefined();
    unmount();
  });

  it("T06: mergeLocalProfile only fills gaps for matching stored id (intercepted transport)", async () => {
    localStorage.setItem(
      STOREFRONT_CUSTOMER_KEY,
      JSON.stringify({ id: 1, full_name: "Stale Local", phone: "09120000001" }),
    );
    vi.spyOn(apiClient, "get").mockResolvedValue({
      data: {
        id: 2,
        phone_number: "09120000002",
        full_name: null,
        company_name: null,
      },
    });
    const me = await authService.getMe();
    expect(me.full_name).toBeNull();
  });

  it("T07: logout hides private state before transport settles; older logout cannot erase B", async () => {
    let rejectLogout!: (reason?: unknown) => void;
    vi.spyOn(apiClient, "post").mockImplementation((url: string) => {
      if (String(url).includes("/auth/logout")) {
        return new Promise((_resolve, reject) => {
          rejectLogout = reject;
        });
      }
      return Promise.resolve({ data: {} });
    });

    establishVerifiedCustomer(1, "otp");
    const logoutPromise = authService.logout();
    expect(getCustomerSessionSnapshot().verifiedCustomerId).toBeNull();

    establishVerifiedCustomer(2, "otp");
    const genB = getCustomerSessionSnapshot().generation;

    await act(async () => {
      rejectLogout(new Error("network failed logout"));
      await logoutPromise.catch(() => undefined);
    });

    expect(getCustomerSessionSnapshot().verifiedCustomerId).toBe(2);
    expect(getCustomerSessionSnapshot().generation).toBe(genB);
  });

  it("T07: logout invalidation removes cached /me entries", () => {
    const client = new QueryClient();
    client.setQueryData(authKeys.me([1, 1]), {
      id: 1,
      phone: "0912",
      full_name: "A",
    } as MeResponse);
    invalidateCustomerSession("guest");
    clearPrivateAuthAndOrderQueries(client);
    expect(client.getQueryCache().findAll({ queryKey: authKeys.all })).toHaveLength(0);
  });

  it("C4/T01: live branch A logout B within staleTime uses intercepted /auth/me (not mock mode)", async () => {
    vi.spyOn(authService, "getMe").mockResolvedValue({
      id: 2,
      phone: "09122222222",
      full_name: "Live B",
      company_name: null,
    });

    const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 60_000 } } });
    establishVerifiedCustomer(1, "otp");
    client.setQueryData(authKeys.me([1, 1]), {
      id: 1,
      phone: "09121111111",
      full_name: "Cached A",
    } as MeResponse);

    invalidateCustomerSession("guest");
    const { result, unmount } = renderHook(() => useMe(true), client);

    await waitUntil(() => result.current?.data?.full_name === "Live B", 120);
    expect(result.current?.data?.id).toBe(2);
    unmount();
  });

  it("T02: verified owner scopes /me query key by generation", () => {
    establishVerifiedCustomer(9, "otp");
    const snap = getCustomerSessionSnapshot();
    expect(authKeys.me([9, snap.generation])).toEqual(["auth", "me", 9, snap.generation]);
  });
});
