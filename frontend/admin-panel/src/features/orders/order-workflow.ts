import type { OrderDetail, OrderStatus } from "@/types/order";

export const PURCHASE_STEPS: OrderStatus[] = [
  "pending_payment",
  "paid",
  "processing",
  "shipped",
  "delivered",
];

export const INQUIRY_STEPS: OrderStatus[] = [
  "inquiry_review",
  "inquiry_quoted",
  "inquiry_closed",
];

export const STATUS_LABELS: Record<OrderStatus, string> = {
  pending_payment: "در انتظار پرداخت",
  paid: "پرداخت شده",
  processing: "در حال پردازش",
  shipped: "ارسال شده",
  delivered: "تحویل شده",
  cancelled: "لغو شده",
  inquiry_review: "بررسی استعلام",
  inquiry_quoted: "پیش‌فاکتور صادر شد",
  inquiry_closed: "پرونده بسته شد",
};

export type OrderActionType = "advance" | "ship" | "quote" | "cancel";

export interface OrderAction {
  type: OrderActionType;
  label: string;
  description: string;
  nextStatus?: OrderStatus;
  variant?: "default" | "destructive" | "outline";
}

const PURCHASE_ACTIONS: Partial<Record<OrderStatus, OrderAction>> = {
  pending_payment: {
    type: "advance",
    label: "تأیید پرداخت",
    description: "پرداخت را به‌صورت دستی تأیید کنید (در صورت نیاز).",
    nextStatus: "paid",
  },
  paid: {
    type: "advance",
    label: "شروع پردازش",
    description: "سفارش را برای آماده‌سازی انبار علامت بزنید.",
    nextStatus: "processing",
  },
  processing: {
    type: "ship",
    label: "ثبت ارسال",
    description: "کد رهگیری پست و زمان تحویل را وارد کنید.",
    nextStatus: "shipped",
  },
  shipped: {
    type: "advance",
    label: "تحویل به مشتری",
    description: "سفارش به دست مشتری رسیده است.",
    nextStatus: "delivered",
  },
};

const INQUIRY_ACTIONS: Partial<Record<OrderStatus, OrderAction>> = {
  inquiry_review: {
    type: "quote",
    label: "صدور پیش‌فاکتور",
    description: "قیمت اقلام را تعیین و پیش‌فاکتور رسمی صادر کنید.",
    nextStatus: "inquiry_quoted",
  },
  inquiry_quoted: {
    type: "advance",
    label: "بستن پرونده",
    description: "پس از هماهنگی با مشتری، پرونده استعلام را ببندید.",
    nextStatus: "inquiry_closed",
  },
};

export function getWorkflowSteps(order: Pick<OrderDetail, "mode">): OrderStatus[] {
  return order.mode === "inquiry" ? INQUIRY_STEPS : PURCHASE_STEPS;
}

export function getPrimaryAction(order: OrderDetail): OrderAction | null {
  if (order.status === "cancelled" || order.status === "delivered" || order.status === "inquiry_closed") {
    return null;
  }

  const map = order.mode === "inquiry" ? INQUIRY_ACTIONS : PURCHASE_ACTIONS;
  return map[order.status] ?? null;
}

export function canCancel(order: OrderDetail): boolean {
  return !["cancelled", "delivered", "inquiry_closed"].includes(order.status);
}

export function stepIndex(steps: OrderStatus[], status: OrderStatus): number {
  const idx = steps.indexOf(status);
  return idx >= 0 ? idx : 0;
}

export function isStepComplete(steps: OrderStatus[], current: OrderStatus, step: OrderStatus): boolean {
  const currentIdx = stepIndex(steps, current);
  const stepIdx = stepIndex(steps, step);
  return stepIdx < currentIdx;
}

export function isStepActive(steps: OrderStatus[], current: OrderStatus, step: OrderStatus): boolean {
  return current === step;
}

export function validateStatusTransition(
  order: Pick<OrderDetail, "mode" | "status">,
  next: OrderStatus,
): string | null {
  if (next === "cancelled") return null;

  const primary = getPrimaryAction(order as OrderDetail);
  if (primary?.nextStatus === next) return null;

  if (order.mode === "purchase" && next === "paid" && order.status === "pending_payment") return null;

  return "این تغییر وضعیت از مسیر مجاز گردش کار نیست.";
}

export function timelineDescription(status: OrderStatus, mode: OrderDetail["mode"]): string {
  const map: Partial<Record<OrderStatus, string>> = {
    paid: "پرداخت سفارش تأیید شد",
    processing: "سفارش وارد مرحله آماده‌سازی شد",
    shipped: "سفارش ارسال شد",
    delivered: "سفارش تحویل مشتری شد",
    inquiry_quoted: "پیش‌فاکتور برای مشتری صادر شد",
    inquiry_closed: "پرونده استعلام بسته شد",
    cancelled: mode === "inquiry" ? "استعلام لغو شد" : "سفارش لغو شد",
  };
  return map[status] ?? STATUS_LABELS[status];
}
