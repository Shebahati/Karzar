import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  CUSTOMER_SESSION_SIGNAL_KEY,
  establishVerifiedCustomer,
  getCustomerSessionSnapshot,
  notifyExternalSessionHint,
  registerCustomerSessionHandlers,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { STOREFRONT_CUSTOMER_KEY } from "@/services/auth";
import { ADDRESS_PERSIST_KEY, useAddressStore } from "@/store/address-store";
import { clearPrivateAuthAndOrderQueries } from "@/features/auth/queries";
import { QueryClient } from "@tanstack/react-query";

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    isLoggedIn: vi.fn(() => true),
  };
});

describe("private session boundary events (T11)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    useAddressStore.setState({ byOwner: {}, addresses: [] });
  });

  it("simulated cross-tab storage signal hides addresses until reverify", () => {
    const client = new QueryClient();
    registerCustomerSessionHandlers({
      onSessionInvalidated: () => {
        clearPrivateAuthAndOrderQueries(client);
        useAddressStore.getState().clearVisibleAddresses();
      },
      onSessionVerified: (ownerId) => {
        useAddressStore.getState().hydrateVisibleForVerifiedOwner(ownerId);
      },
    });

    establishVerifiedCustomer(7, "otp");
    useAddressStore.setState({
      byOwner: {
        "7": [
          {
            id: "a",
            label: "l",
            full_name: "Tab A",
            phone: "0912",
            province: "p",
            city: "c",
            postal_code: "1",
            address_line: "line",
            is_default: true,
          },
        ],
      },
    });
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(7);
    expect(useAddressStore.getState().addresses).toHaveLength(1);

    notifyExternalSessionHint();
    useAddressStore.getState().clearVisibleAddresses();
    expect(useAddressStore.getState().addresses).toHaveLength(0);

    window.dispatchEvent(
      new StorageEvent("storage", {
        key: CUSTOMER_SESSION_SIGNAL_KEY,
        newValue: String(Date.now()),
      }),
    );

    establishVerifiedCustomer(7, "me");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(7);
    expect(useAddressStore.getState().addresses[0]?.full_name).toBe("Tab A");
  });

  it("storage on customer/address keys is wired for cross-tab hints", () => {
    establishVerifiedCustomer(1, "otp");
    notifyExternalSessionHint();
    window.dispatchEvent(
      new StorageEvent("storage", {
        key: STOREFRONT_CUSTOMER_KEY,
        newValue: JSON.stringify({ id: 2 }),
      }),
    );
    window.dispatchEvent(
      new StorageEvent("storage", {
        key: ADDRESS_PERSIST_KEY,
        newValue: "{}",
      }),
    );
    expect(getCustomerSessionSnapshot().verifiedCustomerId).toBeNull();
  });
});
