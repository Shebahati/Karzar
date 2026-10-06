import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  establishVerifiedCustomer,
  invalidateCustomerSession,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import {
  ADDRESS_PERSIST_KEY,
  migrateAddressPersistForTests,
  useAddressStore,
  type AddressInput,
} from "@/store/address-store";

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

  it("C3/T04: legacy main@83949bc persist envelope is discarded on rehydrate (not assigned to hinted customer)", async () => {
    const legacyAddress = {
      id: "legacy-1",
      label: "L",
      full_name: "Legacy Unowned",
      phone: "09120000001",
      province: "P",
      city: "C",
      postal_code: "1234567890",
      address_line: "legacy line",
      is_default: true,
    };
    localStorage.setItem(
      ADDRESS_PERSIST_KEY,
      JSON.stringify({ state: { addresses: [legacyAddress] }, version: 0 }),
    );
    localStorage.setItem(
      "karzar.storefront.customer",
      JSON.stringify({ id: 1, full_name: "Hint A", phone: "09120000001" }),
    );

    await useAddressStore.persist.rehydrate();
    establishVerifiedCustomer(1, "otp");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(1);

    expect(useAddressStore.getState().byOwner["1"]).toBeUndefined();
    expect(useAddressStore.getState().addresses).toHaveLength(0);
    expect(useAddressStore.getState().getDefault()).toBeUndefined();
  });

  it("C3/T04: invalid JSON in storage fails closed without crash", async () => {
    localStorage.setItem(ADDRESS_PERSIST_KEY, "{not-json");
    await expect(useAddressStore.persist.rehydrate()).resolves.not.toThrow();
    expect(useAddressStore.getState().byOwner).toEqual({});
  });

  it("C3/T04: invalid payload shape fails closed on migrate helper", () => {
    expect(migrateAddressPersistForTests({ byOwner: "bad" }).byOwner).toEqual({});
    expect(migrateAddressPersistForTests(null).byOwner).toEqual({});
  });

  it("C3/T04: setItem failure during addAddress does not crash or expose other owner", () => {
    establishVerifiedCustomer(2, "otp");
    useAddressStore.setState({
      byOwner: {
        "1": [{ ...sample, id: "keep-1", is_default: true }],
      },
      addresses: [],
    });
    const setItem = Storage.prototype.setItem;
    Storage.prototype.setItem = () => {
      throw new Error("quota");
    };
    try {
      useAddressStore.getState().hydrateVisibleForVerifiedOwner(2);
      useAddressStore.getState().addAddress({ ...sample, full_name: "B New" });
      expect(useAddressStore.getState().byOwner["1"]?.[0]?.full_name).toBe("کاربر الف");
    } finally {
      Storage.prototype.setItem = setItem;
    }
  });

  it("preserves owner A v2 bucket across A logout → B → logout → A", () => {
    establishVerifiedCustomer(1, "otp");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(1);
    useAddressStore.getState().addAddress({ ...sample, full_name: "Persist A" });

    invalidateCustomerSession("guest");
    useAddressStore.getState().clearVisibleAddresses();

    establishVerifiedCustomer(2, "otp");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(2);
    useAddressStore.getState().addAddress({ ...sample, full_name: "Persist B", phone: "09122222222" });

    invalidateCustomerSession("guest");
    useAddressStore.getState().clearVisibleAddresses();

    establishVerifiedCustomer(1, "otp");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(1);
    expect(useAddressStore.getState().getDefault()?.full_name).toBe("Persist A");
    expect(useAddressStore.getState().byOwner["2"]?.[0]?.full_name).toBe("Persist B");
  });
});
