import type { PaymentCapabilities } from "@/services/payments";

export const EXTERNAL_REFUND_REFERENCE_MAX_LENGTH = 64;

export type RefundOrderSlice = {
  mode: string;
  payment_status: string | null;
  status: string;
};

export function isAutomatedRefundMode(capabilities: PaymentCapabilities | undefined): boolean {
  return capabilities?.refund_mode === "automated";
}

export function isExternalRefundConfirmationMode(
  capabilities: PaymentCapabilities | undefined,
): boolean {
  return capabilities?.refund_mode === "external_confirmation";
}

/** Operator must record or initiate refund while payment is still paid. */
export function isAwaitingRefund(order: RefundOrderSlice): boolean {
  return order.mode === "purchase" && order.payment_status === "paid";
}

/** Refund recorded in Karzar but order not cancelled — reconciliation / resume cancel. */
export function needsCancelAfterExternalRefund(order: RefundOrderSlice): boolean {
  return (
    order.mode === "purchase" &&
    order.payment_status === "refunded" &&
    order.status !== "cancelled"
  );
}

export function showAutomatedRefundAction(
  order: RefundOrderSlice,
  capabilities: PaymentCapabilities | undefined,
): boolean {
  return isAwaitingRefund(order) && isAutomatedRefundMode(capabilities);
}

export function showExternalRefundConfirmationAction(
  order: RefundOrderSlice,
  capabilities: PaymentCapabilities | undefined,
): boolean {
  return isAwaitingRefund(order) && isExternalRefundConfirmationMode(capabilities);
}

export function externalRefundToastMessage(result: {
  cancelled: boolean;
  reconciliation_required: boolean;
}): "success" | "warning" {
  if (result.cancelled && !result.reconciliation_required) {
    return "success";
  }
  return "warning";
}
