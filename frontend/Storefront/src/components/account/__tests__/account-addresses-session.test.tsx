import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AccountAddressesView } from "@/components/account/account-addresses-view";
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
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, isLoggedIn: () => true };
});

async function waitUntil(predicate: () => boolean, attempts = 60) {
  for (let i = 0; i < attempts; i += 1) {
    if (predicate()) return;
    await new Promise((r) => setTimeout(r, 15));
  }
  throw new Error("timeout");
}

describe("AccountAddressesView session (C2/T09)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    useAddressStore.setState({ byOwner: {}, addresses: [] });
    registerCustomerSessionHandlers({
      onSessionInvalidated: () => useAddressStore.getState().clearVisibleAddresses(),
      onSessionVerified: (id) => useAddressStore.getState().hydrateVisibleForVerifiedOwner(id),
    });
  });

  it("clears editing draft on owner switch and save cannot write A draft into B bucket", async () => {
    establishVerifiedCustomer(1, "otp");
    useAddressStore.setState({
      byOwner: {
        "1": [
          {
            id: "a1",
            label: "home",
            full_name: "Existing A",
            phone: "09120000001",
            province: "Tehran",
            city: "Tehran",
            postal_code: "1234567890",
            address_line: "line",
            is_default: true,
          },
        ],
      },
      addresses: [],
    });
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(1);

    const container = document.createElement("div");
    const root: Root = createRoot(container);
    act(() => {
      root.render(<AccountAddressesView />);
    });

    const addBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("آدرس جدید"),
    );
    expect(addBtn).toBeTruthy();
    await act(async () => {
      addBtn?.click();
    });

    const nameInput = container.querySelector('input[placeholder=""]') as HTMLInputElement | null;
    const inputs = container.querySelectorAll("input");
    const fullNameInput = inputs[1] as HTMLInputElement;
    await act(async () => {
      fullNameInput.value = "Draft A Name";
      fullNameInput.dispatchEvent(new Event("input", { bubbles: true }));
    });

    invalidateCustomerSession("guest");
    establishVerifiedCustomer(2, "otp");
    useAddressStore.getState().hydrateVisibleForVerifiedOwner(2);

    await waitUntil(() => !container.textContent?.includes("Draft A Name"));

    const saveBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("ذخیره"),
    );
    if (saveBtn) {
      await act(async () => {
        saveBtn.click();
      });
    }

    expect(useAddressStore.getState().byOwner["2"]).toBeUndefined();
    expect(useAddressStore.getState().byOwner["1"]?.[0]?.full_name).toBe("Existing A");

    act(() => root.unmount());
  });
});
