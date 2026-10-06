import { beforeEach, describe, expect, it } from "vitest";
import {
  establishVerifiedCustomer,
  invalidateCustomerSession,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { useAddressStore } from "@/store/address-store";

describe("account addresses session (T12)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    useAddressStore.setState({ byOwner: {}, addresses: [] });
  });

  it("duplicate same-owner verification keeps persisted addresses", () => {
    establishVerifiedCustomer(4, "otp");
    useAddressStore.setState({
      byOwner: {
        "4": [
          {
            id: "keep",
            label: "x",
            full_name: "Owner Four",
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
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(4);
    establishVerifiedCustomer(4, "me");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(4);
    expect(useAddressStore.getState().addresses).toHaveLength(1);

    invalidateCustomerSession("guest");
    useAddressStore.getState().clearVisibleAddresses();
    expect(useAddressStore.getState().byOwner["4"]).toHaveLength(1);
  });
});
