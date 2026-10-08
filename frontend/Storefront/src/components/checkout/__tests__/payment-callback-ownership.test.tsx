import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PaymentCallbackView } from "@/components/checkout/payment-callback-view";
import {
  establishVerifiedCustomer,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import { savePendingPayment } from "@/lib/pending-payment";
import { cartService } from "@/services/cart";
import { orderService } from "@/services/orders";
import { paymentService } from "@/services/payments";
import { useCartStore } from "@/store/cart-store";
import type { ProductSummary } from "@/types/product";

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

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  useSearchParams: () =>
    new URLSearchParams({
      Authority: "AUTH-1",
      Status: "OK",
    }),
}));

function product(id: number, price: string | null = "1000"): ProductSummary {
  return {
    id,
    sku: `SKU-${id}`,
    name: `Product ${id}`,
    thumbnail: null,
    base_price: price,
    stock_status: "in_stock",
    availability: true,
    is_original: true,
    category: null,
    brand: null,
  };
}

async function waitUntil(predicate: () => boolean, attempts = 80) {
  for (let i = 0; i < attempts; i += 1) {
    if (predicate()) return;
    await act(async () => {
      await new Promise((r) => setTimeout(r, 15));
    });
  }
  throw new Error("timeout");
}

describe("PaymentCallbackView ownership (F03 cold callback)", () => {
  let root: Root;
  let container: HTMLDivElement;

  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
    replace.mockReset();
    useCartStore.setState({ stash: null, cart: [], quote: [], lastSyncError: null });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  it("clears A purchase stash on success without verified session fence; never clears B", async () => {
    savePendingPayment(42, "KZ-A", 1);
    useCartStore.setState({
      stash: {
        attribution: { kind: "customer", customerId: 1 },
        cart: [{ product: product(51), quantity: 2 }],
        quote: [{ product: product(77, null), quantity: 1 }],
      },
      cart: [],
      quote: [],
      lastSyncError: null,
    });

    const clear = vi.spyOn(cartService, "clear").mockImplementation(async () => {});
    vi.spyOn(paymentService, "verify").mockResolvedValue({
      success: true,
      message: "پرداخت موفق",
      tracking_code: "KZ-A",
      order_id: 42,
      status: "paid",
      status_label: "پرداخت شده",
      ref_id: "REF",
    });
    vi.spyOn(orderService, "track").mockResolvedValue({
      tracking_code: "KZ-A",
      status: "paid",
    } as never);

    await act(async () => {
      root.render(<PaymentCallbackView />);
    });

    await waitUntil(() => useCartStore.getState().stash?.cart.length === 0);

    expect(useCartStore.getState().stash?.attribution).toEqual({
      kind: "customer",
      customerId: 1,
    });
    expect(useCartStore.getState().stash?.quote.map((l) => l.product.id)).toEqual([77]);
    expect(clear).not.toHaveBeenCalled();

    // Later /me for A must not revive paid purchase lines.
    establishVerifiedCustomer(1, "otp");
    useCartStore.getState().publishStashForVerifiedCustomer(1);
    expect(useCartStore.getState().cart.some((l) => l.product.id === 51)).toBe(false);

    await act(async () => {
      root.unmount();
    });
    container.remove();
  });

  it("old A pending success does not clear current B stash", async () => {
    savePendingPayment(99, "KZ-OLD-A", 1);
    useCartStore.setState({
      stash: {
        attribution: { kind: "customer", customerId: 2 },
        cart: [{ product: product(70), quantity: 1 }],
        quote: [],
      },
      cart: [{ product: product(70), quantity: 1 }],
      quote: [],
      lastSyncError: null,
    });
    establishVerifiedCustomer(2, "otp");

    const clear = vi.spyOn(cartService, "clear").mockImplementation(async () => {});
    vi.spyOn(paymentService, "verify").mockResolvedValue({
      success: true,
      message: "پرداخت موفق",
      tracking_code: "KZ-OLD-A",
      order_id: 99,
      status: "paid",
      status_label: "پرداخت شده",
      ref_id: "REF",
    });
    vi.spyOn(orderService, "track").mockResolvedValue({
      tracking_code: "KZ-OLD-A",
      status: "paid",
    } as never);

    const before = structuredClone(useCartStore.getState().stash);

    await act(async () => {
      root.render(<PaymentCallbackView />);
    });

    await waitUntil(() => replace.mock.calls.length > 0 || clear.mock.calls.length > 0 || true);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(useCartStore.getState().stash).toEqual(before);
    expect(useCartStore.getState().cart.map((l) => l.product.id)).toEqual([70]);
    expect(clear).not.toHaveBeenCalled();

    await act(async () => {
      root.unmount();
    });
    container.remove();
  });
});
