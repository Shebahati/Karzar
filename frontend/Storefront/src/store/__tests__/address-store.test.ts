import { beforeEach, describe, expect, it } from "vitest";
import {
  establishVerifiedCustomer,
  invalidateCustomerSession,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { migrateAddressPersistForTests } from "@/store/address-store";
import { useAddressStore, type AddressInput } from "@/store/address-store";

const sample: AddressInput = {
  label: "خانه",
  full_name: "کاربر الف",
  phone: "09120000001",
  province: "تهران",
  city: "تهران",
  postal_code: "1234567890",
  address_line: "خیابان تست",
};

describe("address-store owner isolation (F01)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    useAddressStore.setState({ byOwner: {}, addresses: [] });
  });

  it("T01 baseline defect guard: B cannot read A visible addresses after switch", () => {
    establishVerifiedCustomer(1, "otp");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(1);
    useAddressStore.getState().addAddress(sample);
    expect(useAddressStore.getState().addresses[0]?.full_name).toBe("کاربر الف");

    invalidateCustomerSession("guest");
    useAddressStore.getState().clearVisibleAddresses();
    establishVerifiedCustomer(2, "otp");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(2);

    expect(useAddressStore.getState().addresses).toHaveLength(0);
    expect(useAddressStore.getState().getDefault()).toBeUndefined();
  });

  it("T03: restores versioned addresses for returning owner A", () => {
    establishVerifiedCustomer(5, "otp");
    useAddressStore.setState({
      byOwner: {
        "5": [
          {
            id: "a1",
            label: "دفتر",
            full_name: "A User",
            phone: "09121111111",
            province: "اصفهان",
            city: "اصفهان",
            postal_code: "1111111111",
            address_line: "خیابان A",
            is_default: true,
          },
        ],
      },
      addresses: [],
    });
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(5);
    expect(useAddressStore.getState().getDefault()?.full_name).toBe("A User");
  });

  it("T04: legacy unowned persist slice is discarded on migrate", () => {
    const migrated = migrateAddressPersistForTests({
      addresses: [{ id: "legacy", full_name: "x" }],
    });
    expect(migrated.byOwner).toEqual({});
  });

  it("T08: direct getters stay empty without verified owner", () => {
    useAddressStore.setState({
      byOwner: {
        "9": [
          {
            ...sample,
            id: "x",
            is_default: true,
          },
        ],
      },
      addresses: [],
    });
    expect(useAddressStore.getState().getDefault()).toBeUndefined();
  });
});
