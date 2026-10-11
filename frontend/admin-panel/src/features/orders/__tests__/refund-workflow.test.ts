import { describe, expect, it } from "vitest";

import {
  externalRefundToastMessage,
  isAwaitingRefund,
  needsCancelAfterExternalRefund,
  showAutomatedRefundAction,
  showExternalRefundConfirmationAction,
} from "@/features/orders/refund-workflow";
import type { PaymentCapabilities } from "@/services/payments";

const automated: PaymentCapabilities = {
  provider: "mock",
  automated_refund_supported: true,
  external_refund_confirmation_supported: false,
  refund_mode: "automated",
};

const external: PaymentCapabilities = {
  provider: "sep",
  automated_refund_supported: false,
  external_refund_confirmation_supported: true,
  refund_mode: "external_confirmation",
};

const purchasePaid = { mode: "purchase", payment_status: "paid", status: "processing" };
const purchaseRefundedOpen = { mode: "purchase", payment_status: "refunded", status: "paid" };
const purchaseRefundedDone = { mode: "purchase", payment_status: "refunded", status: "cancelled" };

describe("refund-workflow capability branching", () => {
  it("shows automated refund only for paid payment + automated mode", () => {
    expect(showAutomatedRefundAction(purchasePaid, automated)).toBe(true);
    expect(showExternalRefundConfirmationAction(purchasePaid, automated)).toBe(false);
  });

  it("shows external confirmation only for paid payment + external mode", () => {
    expect(showExternalRefundConfirmationAction(purchasePaid, external)).toBe(true);
    expect(showAutomatedRefundAction(purchasePaid, external)).toBe(false);
  });

  it("hides refund actions when payment already refunded", () => {
    expect(isAwaitingRefund(purchaseRefundedOpen)).toBe(false);
    expect(showAutomatedRefundAction(purchaseRefundedOpen, automated)).toBe(false);
    expect(showExternalRefundConfirmationAction(purchaseRefundedOpen, external)).toBe(false);
  });

  it("shows cancel recovery when refunded but not cancelled", () => {
    expect(needsCancelAfterExternalRefund(purchaseRefundedOpen)).toBe(true);
    expect(needsCancelAfterExternalRefund(purchaseRefundedDone)).toBe(false);
  });

  it("maps partial external refund result to warning toast", () => {
    expect(
      externalRefundToastMessage({ cancelled: false, reconciliation_required: true }),
    ).toBe("warning");
    expect(
      externalRefundToastMessage({ cancelled: true, reconciliation_required: false }),
    ).toBe("success");
  });
});
