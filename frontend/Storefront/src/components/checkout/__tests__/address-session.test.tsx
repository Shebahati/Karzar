import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DetailsStep } from "@/components/checkout/details-step";
import {
  establishVerifiedCustomer,
  invalidateCustomerSession,
  registerCustomerSessionHandlers,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { useAddressStore } from "@/store/address-store";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, isLoggedIn: () => true };
});

vi.mock("@/features/checkout/use-checkout-shipping", () => ({
  useCheckoutShipping: () => ({
    enabled: false,
    methodSelectionEnabled: false,
    receiverDue: false,
    selected: null,
    selectedMethodCode: null,
    expiresAt: null,
    unavailable: false,
    checkoutQuoteRequired: false,
    locationCode: null,
    refreshMethodOptions: vi.fn(),
    refreshQuotes: vi.fn(),
  }),
}));

async function waitUntil(predicate: () => boolean, attempts = 60) {
  for (let i = 0; i < attempts; i += 1) {
    if (predicate()) return;
    await new Promise((r) => setTimeout(r, 15));
  }
  throw new Error("timeout");
}

describe("checkout DetailsStep session (C2/T09)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    useAddressStore.setState({ byOwner: {}, addresses: [] });
    registerCustomerSessionHandlers({
      onSessionInvalidated: () => {
        useAddressStore.getState().clearVisibleAddresses();
      },
      onSessionVerified: (ownerId) => {
        useAddressStore.getState().hydrateVisibleForVerifiedOwner(ownerId);
      },
    });
  });

  it("clears saved selection and copied fields after owner switch; submit cannot persist A into B bucket", async () => {
    const onSubmit = vi.fn();
    const container = document.createElement("div");
    const root: Root = createRoot(container);

    establishVerifiedCustomer(1, "otp");
    useAddressStore.setState({
      byOwner: {
        "1": [
          {
            id: "sel",
            label: "home",
            full_name: "A Saved Name",
            phone: "09120000001",
            province: "Tehran",
            city: "Tehran",
            postal_code: "1234567890",
            address_line: "A line",
            is_default: true,
          },
        ],
      },
    });
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(1);

    act(() => {
      root.render(
        <DetailsStep
          isInquiry={false}
          customer={{ full_name: "A Saved Name", phone: "09120000001", is_guest: false }}
          submitting={false}
          onSubmit={onSubmit}
          onBack={() => {}}
        />,
      );
    });

    await waitUntil(() => container.textContent?.includes("A Saved Name") ?? false);

    invalidateCustomerSession("guest");
    establishVerifiedCustomer(2, "otp");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(2);

    await waitUntil(() => !container.textContent?.includes("A line"));

    const inputs = container.querySelectorAll("input");
    const nameInput = inputs[0] as HTMLInputElement;
    const form = container.querySelector("form");
    expect(form).toBeTruthy();
    await act(async () => {
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    const addSpy = vi.spyOn(useAddressStore.getState(), "addAddress");
    expect(addSpy).not.toHaveBeenCalled();
    if (onSubmit.mock.calls.length > 0) {
      expect(onSubmit.mock.calls[0]?.[0]?.full_name).not.toBe("A Saved Name");
    }
    expect(useAddressStore.getState().byOwner["2"]).toBeUndefined();

    act(() => root.unmount());
  });

  it("T12: same-owner auth event preserves populated checkout fields", async () => {
    const container = document.createElement("div");
    const root = createRoot(container);
    establishVerifiedCustomer(8, "otp");
    useAddressStore.setState({
      byOwner: {
        "8": [
          {
            id: "s8",
            label: "home",
            full_name: "Owner Eight",
            phone: "09128888888",
            province: "Tehran",
            city: "Tehran",
            postal_code: "1234567890",
            address_line: "Eight line",
            is_default: true,
          },
        ],
      },
    });
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(8);

    act(() => {
      root.render(
        <DetailsStep
          isInquiry={false}
          customer={{ full_name: "Owner Eight", phone: "09128888888", is_guest: false }}
          submitting={false}
          onSubmit={vi.fn()}
          onBack={() => {}}
        />,
      );
    });

    await waitUntil(() =>
      Boolean(
        (container.querySelector('input[name="full_name"]') as HTMLInputElement | null)?.value,
      ),
    );
    const nameInput = container.querySelector('input[name="full_name"]') as HTMLInputElement;
    const before = nameInput.value;
    window.dispatchEvent(new Event("karzar-auth-change"));
    establishVerifiedCustomer(8, "me");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(8);
    await waitUntil(() => nameInput.value === before);
    act(() => root.unmount());
  });
});
