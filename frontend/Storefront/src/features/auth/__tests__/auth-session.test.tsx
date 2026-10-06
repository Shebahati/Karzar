import { act } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import {
  authKeys,
  clearPrivateAuthAndOrderQueries,
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
        const startGen = getCustomerSessionSnapshot().generation;
        const me = await authService.getMe();
        const mid = getCustomerSessionSnapshot();
        if (mid.verifiedCustomerId != null && mid.verifiedCustomerId !== me.id) {
          throw new Error("ME_STALE_SESSION");
        }
        if (mid.generation !== startGen && mid.verifiedCustomerId !== me.id) {
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

  it("T02: verified owner scopes /me query key by generation", () => {
    establishVerifiedCustomer(9, "otp");
    const snap = getCustomerSessionSnapshot();
    expect(authKeys.me([9, snap.generation])).toEqual(["auth", "me", 9, snap.generation]);
  });
});
