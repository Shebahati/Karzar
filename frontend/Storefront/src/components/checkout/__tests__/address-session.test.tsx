import { beforeEach, describe, expect, it } from "vitest";
import {
  establishVerifiedCustomer,
  invalidateCustomerSession,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { useAddressStore } from "@/store/address-store";

describe("checkout address session (T09)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    useAddressStore.setState({ byOwner: {}, addresses: [] });
  });

  it("clears visible saved addresses when owner invalidates", () => {
    establishVerifiedCustomer(1, "otp");
    useAddressStore.setState({
      byOwner: {
        "1": [
          {
            id: "sel",
            label: "home",
            full_name: "A Name",
            phone: "09120000001",
            province: "t",
            city: "t",
            postal_code: "1234567890",
            address_line: "line",
            is_default: true,
          },
        ],
      },
    });
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(1);
    expect(useAddressStore.getState().getDefault()?.full_name).toBe("A Name");

    invalidateCustomerSession("guest");
    useAddressStore.getState().clearVisibleAddresses();
    establishVerifiedCustomer(2, "otp");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(2);

    expect(useAddressStore.getState().getDefault()).toBeUndefined();
  });
});
