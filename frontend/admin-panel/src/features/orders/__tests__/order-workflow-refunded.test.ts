import { describe, expect, it } from "vitest";

import { getPrimaryAction } from "@/features/orders/order-workflow";
import {
  isAwaitingRefund,
  needsCancelAfterExternalRefund,
  showAutomatedRefundAction,
  showExternalRefundConfirmationAction,
} from "@/features/orders/refund-workflow";
import type { OrderDetail } from "@/types/order";
import type { PaymentCapabilities } from "@/services/payments";

const external: PaymentCapabilities = {
  provider: "sep",
  automated_refund_supported: false,
  external_refund_confirmation_supported: true,
  refund_mode: "external_confirmation",
};

const automated: PaymentCapabilities = {
  provider: "mock",
  automated_refund_supported: true,
  external_refund_confirmation_supported: false,
  refund_mode: "automated",
};

function order(partial: Partial<OrderDetail>): OrderDetail {
  return {
    id: 1,
    tracking_code: "KZ-TEST",
    mode: "purchase",
    status: "paid",
    payment_status: "paid",
    shipments: [],
    ...partial,
  } as OrderDetail;
}

describe("refunded partial-state admin workflow", () => {
  it("hides primary fulfillment actions when refunded but not cancelled", () => {
    for (const status of ["paid", "processing", "shipped"] as const) {
      const o = order({ payment_status: "refunded", status });
      expect(getPrimaryAction(o)).toBeNull();
    }
  });

  it("shows recovery and hides refund actions in partial state", () => {
    const o = order({ payment_status: "refunded", status: "processing" });
    expect(isAwaitingRefund(o)).toBe(false);
    expect(needsCancelAfterExternalRefund(o)).toBe(true);
    expect(showAutomatedRefundAction(o, automated)).toBe(false);
    expect(showExternalRefundConfirmationAction(o, external)).toBe(false);
  });

  it("shows no recovery when refunded and cancelled", () => {
    const o = order({ payment_status: "refunded", status: "cancelled" });
    expect(needsCancelAfterExternalRefund(o)).toBe(false);
    expect(getPrimaryAction(o)).toBeNull();
  });
});
