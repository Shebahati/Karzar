import { beforeEach, describe, expect, it } from "vitest";
import {
  establishVerifiedCustomer,
  invalidateCustomerSession,
  isPrivateDataEnabled,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { useAddressStore } from "@/store/address-store";

describe("invoice/proforma address getters (T10)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    useAddressStore.setState({ byOwner: {}, addresses: [] });
  });

  it("direct getDefault returns undefined for unknown session even if byOwner has A data", () => {
    useAddressStore.setState({
      byOwner: {
        "1": [
          {
            id: "a",
            label: "l",
            full_name: "Secret A",
            phone: "0912",
            province: "p",
            city: "c",
            postal_code: "1234567890",
            address_line: "line",
            is_default: true,
          },
        ],
      },
      addresses: [],
    });
    expect(useAddressStore.getState().getDefault()).toBeUndefined();
  });

  it("captured getter closure respects later invalidation", () => {
    establishVerifiedCustomer(1, "otp");
    useAddressStore.setState({
      byOwner: {
        "1": [
          {
            id: "a",
            label: "l",
            full_name: "Secret A",
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
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(1);
    const snapshotGetter = () => useAddressStore.getState().getDefault();
    expect(snapshotGetter()?.full_name).toBe("Secret A");

    invalidateCustomerSession("guest");
    useAddressStore.getState().clearVisibleAddresses();
    expect(isPrivateDataEnabled()).toBe(false);
    expect(snapshotGetter()?.full_name).toBeUndefined();
  });
});
