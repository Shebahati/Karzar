import { act, useLayoutEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, useQueryClient } from "@tanstack/react-query";
import { Providers } from "@/app/providers";
import { useMe } from "@/features/auth/queries";
import { useMyOrders } from "@/features/orders/queries";
import {
  CUSTOMER_SESSION_SIGNAL_KEY,
  establishVerifiedCustomer,
  getCustomerSessionSnapshot,
  isPrivateDataEnabled,
  notifyExternalSessionHint,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { authService, STOREFRONT_CUSTOMER_KEY } from "@/services/auth";
import { orderService } from "@/services/orders";
import { ADDRESS_PERSIST_KEY, useAddressStore } from "@/store/address-store";

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

vi.mock("@/lib/feature-labels", () => ({
  loadFeatureLabels: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/store/cart-store", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/store/cart-store")>();
  return {
    ...actual,
    useCartStore: Object.assign(actual.useCartStore, {
      persist: { rehydrate: vi.fn().mockResolvedValue(undefined) },
    }),
  };
});

const isLoggedInMock = vi.fn(() => true);
vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    isLoggedIn: (...args: unknown[]) => isLoggedInMock(...(args as [])),
    tokenStorage: {
      ...actual.tokenStorage,
      isExpired: () => false,
      clear: vi.fn(),
    },
  };
});

async function waitUntil(predicate: () => boolean, attempts = 80) {
  for (let i = 0; i < attempts; i += 1) {
    if (predicate()) return;
    await new Promise((r) => setTimeout(r, 15));
  }
  throw new Error("timeout");
}

function SessionProbe() {
  const { data: me, isFetching, fetchStatus } = useMe(true);
  const orders = useMyOrders({ limit: 5 });
  const addresses = useAddressStore((s) => s.addresses);
  const snap = getCustomerSessionSnapshot();
  return (
    <div>
      <span data-testid="me-name">{me?.full_name ?? ""}</span>
      <span data-testid="me-id">{me?.id ?? ""}</span>
      <span data-testid="me-fetching">{String(isFetching)}</span>
      <span data-testid="me-status">{fetchStatus}</span>
      <span data-testid="orders-enabled">{String(orders.isFetching || orders.isFetched)}</span>
      <span data-testid="orders-data">{orders.data?.data?.[0]?.tracking_code ?? ""}</span>
      <span data-testid="addr-count">{addresses.length}</span>
      <span data-testid="addr-name">{addresses[0]?.full_name ?? ""}</span>
      <span data-testid="generation">{snap.generation}</span>
      <span data-testid="verified">{snap.verifiedCustomerId ?? "none"}</span>
    </div>
  );
}

function mountProviders() {
  const container = document.createElement("div");
  const root: Root = createRoot(container);
  act(() => {
    root.render(
      <Providers>
        <SessionProbe />
      </Providers>,
    );
  });
  return { container, root, unmount: () => act(() => root.unmount()) };
}

describe("Providers private session boundary", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    isLoggedInMock.mockReturnValue(true);
    vi.restoreAllMocks();
  });

  it("C1/T02: cold bootstrap hides A data until /me resolves as B (intercepted transport)", async () => {
    const addressA = {
      id: "a-addr",
      label: "home",
      full_name: "Address Owner A",
      phone: "09120000001",
      province: "Tehran",
      city: "Tehran",
      postal_code: "1234567890",
      address_line: "A street",
      is_default: true,
    };
    localStorage.setItem(
      STOREFRONT_CUSTOMER_KEY,
      JSON.stringify({ id: 1, full_name: "Cached A Profile", phone: "09120000001" }),
    );
    localStorage.setItem(
      ADDRESS_PERSIST_KEY,
      JSON.stringify({
        state: { byOwner: { "1": [addressA] } },
        version: 2,
      }),
    );

    let firstPending = true;
    let resolveAllMe!: (me: Awaited<ReturnType<typeof authService.getMe>>) => void;
    const getMeSpy = vi.spyOn(authService, "getMe").mockImplementation(async () => {
      if (firstPending) {
        firstPending = false;
        return new Promise((resolve) => {
          resolveAllMe = resolve;
        });
      }
      return {
        id: 2,
        phone: "09122222222",
        full_name: "Server User B",
        company_name: null,
      };
    });
    const listSpy = vi.spyOn(orderService, "listMine").mockResolvedValue({
      data: [
        {
          id: 99,
          tracking_code: "ORD-A-LEAK",
          mode: "purchase",
          status: "pending_payment",
          status_label: "pending",
          created_at: "2026-01-01T00:00:00Z",
          estimated_total: "0",
        },
      ],
      meta: { total_count: 1, skip: 0, limit: 5, has_next: false, has_prev: false },
    });

    const { container, unmount } = mountProviders();
    await act(async () => {
      await useAddressStore.persist.rehydrate();
    });

    await waitUntil(() => getMeSpy.mock.calls.length > 0);

    expect(container.querySelector('[data-testid="me-name"]')?.textContent).toBe("");
    expect(container.querySelector('[data-testid="addr-name"]')?.textContent).toBe("");
    expect(container.textContent).not.toContain("Cached A Profile");
    expect(listSpy).not.toHaveBeenCalled();

    const genBeforeResolve = Number(container.querySelector('[data-testid="generation"]')?.textContent);
    await act(async () => {
      resolveAllMe({
        id: 2,
        phone: "09122222222",
        full_name: "Server User B",
        company_name: null,
      });
    });

    await waitUntil(
      () => container.querySelector('[data-testid="me-name"]')?.textContent === "Server User B",
    );
    expect(container.querySelector('[data-testid="verified"]')?.textContent).toBe("2");
    expect(container.textContent).not.toContain("Address Owner A");
    expect(container.textContent).not.toContain("Cached A Profile");
    await waitUntil(() => listSpy.mock.calls.length > 0);
    expect(container.querySelector('[data-testid="orders-data"]')?.textContent).toBe("ORD-A-LEAK");
    expect(Number(container.querySelector('[data-testid="generation"]')?.textContent)).toBe(
      genBeforeResolve,
    );

    unmount();
  });

  it("T11: mounted Providers refetch /me after simulated cross-tab storage and visibility return", async () => {
    let calls = 0;
    vi.spyOn(authService, "getMe").mockImplementation(async () => {
      calls += 1;
      return {
        id: 3,
        phone: "09123333333",
        full_name: `Verified call ${calls}`,
        company_name: null,
      };
    });

    const { container, unmount } = mountProviders();
    await waitUntil(() => (container.textContent?.includes("Verified call") ?? false));
    await waitUntil(() => getCustomerSessionSnapshot().verifiedCustomerId === 3);

    useAddressStore.setState({
      byOwner: {
        "3": [
          {
            id: "x",
            label: "l",
            full_name: "Visible Three",
            phone: "0912",
            province: "p",
            city: "c",
            postal_code: "1234567890",
            address_line: "line",
            is_default: true,
          },
        ],
      },
    });
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(3);
    expect(useAddressStore.getState().addresses.length).toBe(1);

    window.dispatchEvent(
      new StorageEvent("storage", {
        key: STOREFRONT_CUSTOMER_KEY,
        newValue: JSON.stringify({ id: 99, phone: "09129999999" }),
      }),
    );
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => "visible",
    });
    document.dispatchEvent(new Event("visibilitychange"));

    await waitUntil(() => useAddressStore.getState().addresses.length === 0);
    expect(calls).toBeGreaterThanOrEqual(1);
    unmount();
  });

  it("T11: external CUSTOMER_SESSION_SIGNAL_KEY is receiver-only (no rebroadcast)", async () => {
    let calls = 0;
    vi.spyOn(authService, "getMe").mockImplementation(async () => {
      calls += 1;
      return {
        id: 3,
        phone: "09123333333",
        full_name: `Owner Three #${calls}`,
        company_name: null,
      };
    });
    vi.spyOn(orderService, "listMine").mockResolvedValue({
      data: [],
      meta: { total_count: 0, skip: 0, limit: 5, has_next: false, has_prev: false },
    });

    const { container, unmount } = mountProviders();
    await waitUntil(() => getCustomerSessionSnapshot().verifiedCustomerId === 3);
    await waitUntil(() =>
      (container.querySelector('[data-testid="me-name"]')?.textContent ?? "").startsWith(
        "Owner Three",
      ),
    );

    useAddressStore.setState({
      byOwner: {
        "3": [
          {
            id: "x",
            label: "l",
            full_name: "Visible Three",
            phone: "0912",
            province: "p",
            city: "c",
            postal_code: "1234567890",
            address_line: "line",
            is_default: true,
          },
        ],
      },
    });
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(3);
    expect(useAddressStore.getState().addresses.length).toBe(1);
    const genVerified = getCustomerSessionSnapshot().generation;
    const callsAfterVerify = calls;

    localStorage.removeItem(CUSTOMER_SESSION_SIGNAL_KEY);
    const setItemSpy = vi.spyOn(window.localStorage, "setItem");
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: CUSTOMER_SESSION_SIGNAL_KEY,
          newValue: String(Date.now()),
        }),
      );
    });

    // Assert receiver-only transition synchronously before async /me reverify.
    const snapAfterHint = getCustomerSessionSnapshot();
    expect(snapAfterHint.phase).toBe("checking");
    expect(snapAfterHint.verifiedCustomerId).toBeNull();
    expect(snapAfterHint.generation).toBeGreaterThan(genVerified);
    expect(isPrivateDataEnabled()).toBe(false);
    expect(useAddressStore.getState().addresses).toHaveLength(0);
    expect(
      setItemSpy.mock.calls.filter(([key]) => key === CUSTOMER_SESSION_SIGNAL_KEY),
    ).toHaveLength(0);
    expect(localStorage.getItem(CUSTOMER_SESSION_SIGNAL_KEY)).toBeNull();

    await waitUntil(() => getCustomerSessionSnapshot().verifiedCustomerId === 3);
    await waitUntil(() =>
      (container.querySelector('[data-testid="me-name"]')?.textContent ?? "").startsWith(
        "Owner Three",
      ),
    );
    expect(isPrivateDataEnabled()).toBe(true);
    expect(calls).toBeGreaterThan(callsAfterVerify);
    expect(
      setItemSpy.mock.calls.filter(([key]) => key === CUSTOMER_SESSION_SIGNAL_KEY),
    ).toHaveLength(0);
    expect(localStorage.getItem(CUSTOMER_SESSION_SIGNAL_KEY)).toBeNull();

    unmount();
  });

  it("T11: external STOREFRONT_CUSTOMER_KEY / ADDRESS_PERSIST_KEY hints do not rebroadcast", async () => {
    vi.spyOn(authService, "getMe").mockResolvedValue({
      id: 8,
      phone: "09128888888",
      full_name: "Owner Eight",
      company_name: null,
    });

    const { unmount } = mountProviders();
    await waitUntil(() => getCustomerSessionSnapshot().verifiedCustomerId === 8);

    const assertNoSignalBroadcast = (key: string, newValue: string) => {
      localStorage.removeItem(CUSTOMER_SESSION_SIGNAL_KEY);
      const setItemSpy = vi.spyOn(window.localStorage, "setItem");
      act(() => {
        window.dispatchEvent(new StorageEvent("storage", { key, newValue }));
      });
      expect(getCustomerSessionSnapshot().phase).toBe("checking");
      expect(
        setItemSpy.mock.calls.filter(([k]) => k === CUSTOMER_SESSION_SIGNAL_KEY),
      ).toHaveLength(0);
      expect(localStorage.getItem(CUSTOMER_SESSION_SIGNAL_KEY)).toBeNull();
      setItemSpy.mockRestore();
    };

    assertNoSignalBroadcast(
      STOREFRONT_CUSTOMER_KEY,
      JSON.stringify({ id: 99, phone: "09129999999" }),
    );
    // Re-establish so the second hint again starts from verified.
    establishVerifiedCustomer(8, "me");
    assertNoSignalBroadcast(
      ADDRESS_PERSIST_KEY,
      JSON.stringify({ state: { byOwner: {} }, version: 2 }),
    );

    unmount();
  });

  it("T12: duplicate same-session auth-change does not wipe generation or addresses", async () => {
    const getMeSpy = vi.spyOn(authService, "getMe").mockResolvedValue({
      id: 4,
      phone: "09124444444",
      full_name: "Stable Four",
      company_name: null,
    });

    const { container, unmount } = mountProviders();
    await waitUntil(
      () => container.querySelector('[data-testid="me-name"]')?.textContent === "Stable Four",
    );

    useAddressStore.setState({
      byOwner: {
        "4": [
          {
            id: "keep",
            label: "k",
            full_name: "Stable Address",
            phone: "09124444444",
            province: "p",
            city: "c",
            postal_code: "1234567890",
            address_line: "line",
            is_default: true,
          },
        ],
      },
    });
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(4);
    const gen = Number(container.querySelector('[data-testid="generation"]')?.textContent);
    const callsBefore = getMeSpy.mock.calls.length;

    window.dispatchEvent(new Event("karzar-auth-change"));
    window.dispatchEvent(new Event("karzar-auth-change"));

    await waitUntil(() => useAddressStore.getState().addresses[0]?.full_name === "Stable Address");
    expect(Number(container.querySelector('[data-testid="generation"]')?.textContent)).toBe(gen);
    expect(getMeSpy.mock.calls.length).toBeGreaterThanOrEqual(callsBefore);

    unmount();
  });

  it("T08/T11: public catalog query survives private invalidation", async () => {
    vi.spyOn(authService, "getMe").mockResolvedValue({
      id: 5,
      phone: "0912",
      full_name: "Five",
      company_name: null,
    });

    function CatalogProbe() {
      const client = useQueryClient();
      const catalog = client.getQueryData(["catalog", "featured"]);
      return <span data-testid="catalog">{JSON.stringify(catalog ?? null)}</span>;
    }

    const container = document.createElement("div");
    const root = createRoot(container);
    const clientRef: { current: QueryClient | null } = { current: null };

    function SeedCatalog() {
      const client = useQueryClient();
      useLayoutEffect(() => {
        clientRef.current = client;
        client.setQueryData(["catalog", "featured"], { items: [1] });
      }, [client]);
      return <CatalogProbe />;
    }

    act(() => {
      root.render(
        <Providers>
          <SeedCatalog />
        </Providers>,
      );
    });

    establishVerifiedCustomer(5, "otp");
    notifyExternalSessionHint();
    const cachedCatalog = clientRef.current?.getQueryData(["catalog", "featured"]);
    expect(cachedCatalog).toEqual({ items: [1] });
    act(() => root.unmount());
  });
});
