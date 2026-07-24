/** Shared storefront constants. */

export const ERROR_CODES = {
  GUEST_ORDER_NOT_PAYABLE: "GUEST_ORDER_NOT_PAYABLE",
} as const;

export const PAYMENT_PENDING_ORDER_KEY = "karzar.payment.pending_order";

export const ORDER_STATUS_LABELS: Record<
  import("@/types/order").OrderStatus,
  string
> = {
  pending_payment: "در انتظار پرداخت",
  paid: "پرداخت شده",
  processing: "در حال پردازش",
  shipped: "ارسال شده",
  delivered: "تحویل شده",
  cancelled: "لغو شده",
  inquiry_review: "در حال بررسی استعلام",
  inquiry_quoted: "پیش‌فاکتور صادر شد",
  inquiry_closed: "پرونده بسته شد",
};
