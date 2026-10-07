import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthStep } from "@/components/checkout/auth-step";
import {
  establishVerifiedCustomer,
  getCustomerSessionSnapshot,
  invalidateCustomerSession,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { savePendingInquiry, getPendingInquiry } from "@/lib/inquiry-pending";
import { authService } from "@/services/auth";
import { catalogService } from "@/services/catalog";
import { cartService } from "@/services/cart";
import { useCartStore } from "@/store/cart-store";

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

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    isLoggedIn: () => true,
    setStoredToken: vi.fn(),
  };
});

async function waitUntil(predicate: () => boolean, attempts = 80) {
  for (let i = 0; i < attempts; i += 1) {
    if (predicate()) return;
    await new Promise((r) => setTimeout(r, 15));
  }
  throw new Error("timeout");
}

function emptyCart(lane: "purchase" | "inquiry") {
  return { lane, items: [] as { product_id: number; quantity: number }[], item_count: 0 };
}

describe("AuthStep pending inquiry restore ownership (F03)", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
    useCartStore.setState({ stash: null, cart: [], quote: [], lastSyncError: null });
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => emptyCart(lane));
    vi.spyOn(cartService, "upsertItem").mockResolvedValue(emptyCart("purchase"));
    vi.spyOn(cartService, "merge").mockResolvedValue([]);
  });

  it("T13: late A pending-inquiry restore cannot enter B", async () => {
    const phone = "09120000001";
    savePendingInquiry(phone, {
      full_name: "User A",
      tracking_code: "T-A",
      created_at: new Date().toISOString(),
      lines: [{ product_id: 51, quantity: 2 }],
    });

    let resolveProducts!: (products: Array<{
      id: number;
      sku: string;
      name: string;
      thumbnail: string | null;
      base_price: string | null;
    }>) => void;
    const productsGate = new Promise<
      Array<{
        id: number;
        sku: string;
        name: string;
        thumbnail: string | null;
        base_price: string | null;
      }>
    >((resolve) => {
      resolveProducts = resolve;
    });

    vi.spyOn(authService, "verifyOtp").mockImplementation(async () => {
      establishVerifiedCustomer(1, "otp");
      return {
        access_token: "a",
        refresh_token: "r",
        token_type: "bearer",
        expires_in: 1800,
        customer: { id: 1, phone, full_name: "User A" },
        cart_sync_error: null,
      };
    });
    vi.spyOn(authService, "getMe").mockResolvedValue({
      id: 1,
      phone,
      full_name: "User A",
      company_name: null,
    });
    vi.spyOn(catalogService, "getProductsByIds").mockImplementation(
      async () =>
        (await productsGate).map((p) => ({
          ...p,
          stock_status: "in_stock" as const,
          availability: true,
          is_original: true,
          category: null,
          brand: null,
        })),
    );

    const onResolved = vi.fn();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root: Root = createRoot(container);

    act(() => {
      root.render(
        <QueryClientProvider client={client}>
          <AuthStep isInquiry onResolved={onResolved} />
        </QueryClientProvider>,
      );
    });

    vi.spyOn(authService, "requestOtp").mockResolvedValue({
      phone,
      expires_in: 120,
      dev_code: "111111",
    });

    await waitUntil(() =>
      Array.from(container.querySelectorAll("button")).some((b) =>
        /ورود با کد یک‌بارمصرف/i.test(b.textContent ?? ""),
      ),
    );
    const otpChoice = Array.from(container.querySelectorAll("button")).find((b) =>
      /ورود با کد یک‌بارمصرف/i.test(b.textContent ?? ""),
    );
    await act(async () => {
      otpChoice!.click();
    });

    await waitUntil(() => !!container.querySelector('input[inputmode="tel"]'));
    const phoneInput = container.querySelector('input[inputmode="tel"]') as HTMLInputElement;
    const nativeSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      "value",
    )?.set;
    act(() => {
      nativeSetter?.call(phoneInput, phone);
      phoneInput.dispatchEvent(new Event("input", { bubbles: true }));
      phoneInput.dispatchEvent(new Event("change", { bubbles: true }));
    });
    const requestBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      /دریافت کد/i.test(b.textContent ?? ""),
    );
    expect(requestBtn).toBeTruthy();
    await act(async () => {
      requestBtn!.click();
    });

    await waitUntil(() => !!container.querySelector('input[inputmode="numeric"]'));
    const otpInput = container.querySelector('input[inputmode="numeric"]') as HTMLInputElement;
    act(() => {
      nativeSetter?.call(otpInput, "111111");
      otpInput.dispatchEvent(new Event("input", { bubbles: true }));
      otpInput.dispatchEvent(new Event("change", { bubbles: true }));
    });
    const verifyBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      /تأیید/i.test(b.textContent ?? ""),
    );
    expect(verifyBtn).toBeTruthy();
    await act(async () => {
      verifyBtn!.click();
    });

    await waitUntil(() => (catalogService.getProductsByIds as ReturnType<typeof vi.fn>).mock.calls.length > 0);
    expect(getCustomerSessionSnapshot().verifiedCustomerId).toBe(1);

    // Switch to B before A catalog resolves.
    invalidateCustomerSession("guest");
    useCartStore.getState().hidePublishedCart();
    establishVerifiedCustomer(2, "otp");
    useCartStore.setState({
      stash: {
        attribution: { kind: "customer", customerId: 2 },
        cart: [],
        quote: [],
      },
      cart: [],
      quote: [],
      lastSyncError: null,
    });

    await act(async () => {
      resolveProducts([
        {
          id: 51,
          sku: "SKU-51",
          name: "Inquiry A",
          thumbnail: null,
          base_price: null,
        },
      ]);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(useCartStore.getState().quote.some((l) => l.product.id === 51)).toBe(false);
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 2,
    });
    expect(sessionStorage.getItem("karzar.inquiry.restored")).toBeNull();
    expect(getPendingInquiry(phone)?.lines[0]?.product_id).toBe(51);

    act(() => root.unmount());
    container.remove();
  });

  it("T16: valid same-owner pending restore still works", async () => {
    const phone = "09120000001";
    savePendingInquiry(phone, {
      full_name: "User A",
      tracking_code: "T-A",
      created_at: new Date().toISOString(),
      lines: [{ product_id: 51, quantity: 2 }],
    });

    vi.spyOn(authService, "verifyOtp").mockImplementation(async () => {
      establishVerifiedCustomer(1, "otp");
      useCartStore.setState({
        stash: {
          attribution: { kind: "customer", customerId: 1 },
          cart: [],
          quote: [],
        },
        cart: [],
        quote: [],
        lastSyncError: null,
      });
      return {
        access_token: "a",
        refresh_token: "r",
        token_type: "bearer",
        expires_in: 1800,
        customer: { id: 1, phone, full_name: "User A" },
        cart_sync_error: null,
      };
    });
    vi.spyOn(authService, "getMe").mockResolvedValue({
      id: 1,
      phone,
      full_name: "User A",
      company_name: null,
    });
    vi.spyOn(authService, "requestOtp").mockResolvedValue({
      phone,
      expires_in: 120,
      dev_code: "111111",
    });
    vi.spyOn(catalogService, "getProductsByIds").mockResolvedValue([
      {
        id: 51,
        sku: "SKU-51",
        name: "Inquiry A",
        thumbnail: null,
        base_price: null,
        stock_status: "in_stock",
        availability: true,
        is_original: true,
        category: null,
        brand: null,
      },
    ]);

    const onResolved = vi.fn();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root: Root = createRoot(container);

    act(() => {
      root.render(
        <QueryClientProvider client={client}>
          <AuthStep isInquiry onResolved={onResolved} />
        </QueryClientProvider>,
      );
    });

    await waitUntil(() =>
      Array.from(container.querySelectorAll("button")).some((b) =>
        /ورود با کد یک‌بارمصرف/i.test(b.textContent ?? ""),
      ),
    );
    const otpChoice = Array.from(container.querySelectorAll("button")).find((b) =>
      /ورود با کد یک‌بارمصرف/i.test(b.textContent ?? ""),
    );
    await act(async () => {
      otpChoice!.click();
    });
    await waitUntil(() => !!container.querySelector('input[inputmode="tel"]'));
    const phoneInput = container.querySelector('input[inputmode="tel"]') as HTMLInputElement;
    const nativeSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      "value",
    )?.set;
    act(() => {
      nativeSetter?.call(phoneInput, phone);
      phoneInput.dispatchEvent(new Event("input", { bubbles: true }));
      phoneInput.dispatchEvent(new Event("change", { bubbles: true }));
    });
    const requestBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      /دریافت کد/i.test(b.textContent ?? ""),
    );
    await act(async () => {
      requestBtn!.click();
    });
    await waitUntil(() => !!container.querySelector('input[inputmode="numeric"]'));
    const otpInput = container.querySelector('input[inputmode="numeric"]') as HTMLInputElement;
    act(() => {
      nativeSetter?.call(otpInput, "111111");
      otpInput.dispatchEvent(new Event("input", { bubbles: true }));
      otpInput.dispatchEvent(new Event("change", { bubbles: true }));
    });
    const verifyBtn = Array.from(container.querySelectorAll("button")).find((b) =>
      /تأیید/i.test(b.textContent ?? ""),
    );
    await act(async () => {
      verifyBtn!.click();
    });

    await waitUntil(() => useCartStore.getState().quote.some((l) => l.product.id === 51));
    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 1,
    });
    expect(sessionStorage.getItem("karzar.inquiry.restored")).toBe("1");
    expect(getPendingInquiry(phone)).toBeNull();

    act(() => root.unmount());
    container.remove();
  });
});
