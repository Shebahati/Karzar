import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CheckoutView } from "@/components/checkout/checkout-view";
import type { DetailsResult } from "@/components/checkout/details-step";
import {
  establishVerifiedCustomer,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";
import {
  clearPendingPayment,
  readPendingPayment,
  savePendingPaymentPreservingOwner,
} from "@/lib/pending-payment";
import { cartService } from "@/services/cart";
import { catalogService } from "@/services/catalog";
import { useCartStore } from "@/store/cart-store";
import type { CheckoutPayload, CheckoutResponse } from "@/types/checkout";
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

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    isLoggedIn: () => true,
  };
});

vi.mock("@/features/commerce/use-purchase-checkout-status", () => ({
  usePurchaseCheckoutStatus: () => ({
    data: { purchase_checkout_enabled: true, message: null },
    isLoading: false,
    isPending: false,
  }),
}));

vi.mock("@/features/auth/queries", () => ({
  useMe: () => ({
    data: { id: 1, phone: "09120000001", full_name: "Customer A" },
  }),
  useCustomerSessionSnapshot: () => ({
    phase: "verified",
    verifiedCustomerId: 1,
    generation: 1,
  }),
}));

vi.mock("@/components/checkout/auth-step", () => ({
  AuthStep: () => <div data-testid="auth-step" />,
}));

vi.mock("@/components/checkout/order-summary", () => ({
  OrderSummary: () => <div data-testid="order-summary" />,
}));

vi.mock("@/components/checkout/details-step", () => ({
  DetailsStep: ({ onSubmit }: { onSubmit: (r: DetailsResult) => void }) => (
    <button
      type="button"
      data-testid="submit-details"
      onClick={() =>
        onSubmit({
          full_name: "Customer A",
          phone: "09120000001",
          shipping: {
            province: "تهران",
            city: "تهران",
            postal_code: "1234567890",
            address_line: "خیابان تست",
          },
          shipping_quote_token: "tok",
          shipping_method_code: "tipax",
        })
      }
    >
      submit
    </button>
  ),
}));

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

type MutateArgs = {
  onSuccess?: (res: CheckoutResponse) => void | Promise<void>;
  onError?: (err: Error) => void;
};

let heldMutate: {
  payload: CheckoutPayload;
  opts: MutateArgs;
} | null = null;

const mutate = vi.fn((payload: CheckoutPayload, opts: MutateArgs) => {
  heldMutate = { payload, opts };
});

const initPaymentAsync = vi.fn();

vi.mock("@/features/checkout/queries", () => ({
  useSubmitCheckout: () => ({ mutate, isPending: false, isError: false }),
  useInitPayment: () => ({ mutateAsync: initPaymentAsync, isPending: false }),
}));

function product(id: number): ProductSummary {
  return {
    id,
    sku: `SKU-${id}`,
    name: `Product ${id}`,
    thumbnail: null,
    base_price: "1000",
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

describe("CheckoutView submit-time purchase owner (F03 Blocker 8)", () => {
  let root: Root;
  let container: HTMLDivElement;

  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    sessionStorage.clear();
    clearPendingPayment();
    vi.clearAllMocks();
    heldMutate = null;
    initPaymentAsync.mockRejectedValue(new Error("gateway down"));
    useCartStore.setState({
      stash: {
        attribution: { kind: "customer", customerId: 1 },
        cart: [{ product: product(51), quantity: 1 }],
        quote: [],
      },
      cart: [{ product: product(51), quantity: 1 }],
      quote: [],
      lastSyncError: null,
    });
    vi.spyOn(cartService, "get").mockImplementation(async (lane = "purchase") => ({
      lane,
      items: lane === "purchase" ? [{ product_id: 51, quantity: 1 }] : [],
      item_count: lane === "purchase" ? 1 : 0,
    }));
    vi.spyOn(cartService, "upsertItem").mockResolvedValue({
      lane: "purchase",
      items: [{ product_id: 51, quantity: 1 }],
      item_count: 1,
    });
    vi.spyOn(catalogService, "getProductsByIds").mockResolvedValue([product(51)]);
    establishVerifiedCustomer(1, "otp");
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  it("T27: pending payment owner stays A after A→B mid-submit; A callback cannot clear B", async () => {
    await act(async () => {
      root.render(<CheckoutView />);
    });

    await waitUntil(() => Boolean(container.querySelector('[data-testid="submit-details"]')));

    await act(async () => {
      container.querySelector<HTMLButtonElement>('[data-testid="submit-details"]')?.click();
    });

    await waitUntil(() => heldMutate != null);

    // Session switches to B while A's checkout response is still pending.
    establishVerifiedCustomer(2, "otp");
    useCartStore.setState({
      stash: {
        attribution: { kind: "customer", customerId: 2 },
        cart: [{ product: product(70), quantity: 1 }],
        quote: [],
      },
      cart: [{ product: product(70), quantity: 1 }],
      quote: [],
    });

    const res: CheckoutResponse = {
      order_id: 42,
      tracking_code: "KZ-A",
      mode: "purchase",
      status: "pending_payment",
      status_label: "در انتظار پرداخت",
      estimated_total: "1000",
      created_at: new Date().toISOString(),
      payment_url: null,
    };

    await act(async () => {
      await heldMutate!.opts.onSuccess?.(res);
    });

    expect(readPendingPayment()?.customer_id).toBe(1);
    expect(readPendingPayment()?.customer_id).not.toBe(2);

    // Retry state / preserve path also keeps A.
    const preserved = savePendingPaymentPreservingOwner(42, "KZ-A", 2);
    expect(preserved).toBe(true);
    expect(readPendingPayment()?.customer_id).toBe(1);

    // A callback must not clear B's purchase stash.
    const clear = vi.spyOn(cartService, "clear").mockImplementation(async () => {});
    const cleaned = useCartStore.getState().clearPurchaseCartLocallyForExpectedOwner(1);
    expect(cleaned).toBe(false);
    expect(useCartStore.getState().cart.map((l) => l.product.id)).toEqual([70]);
    expect(clear).not.toHaveBeenCalled();

    await act(async () => {
      root.unmount();
    });
    container.remove();
  });
});
