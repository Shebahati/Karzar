import type { OrderStatus, OrderTrackingEvent } from "@/types/order";

export interface TimelineContext {
  status: OrderStatus;
  mode: "purchase" | "inquiry";
  created_at: string;
  postal_tracking_code?: string | null;
  delivery_eta?: string | null;
}

const PURCHASE_STAGES: Array<{
  status: OrderStatus;
  label: string;
  description: (ctx: TimelineContext) => string | null;
}> = [
  {
    status: "pending_payment",
    label: "ثبت سفارش",
    description: () => "سفارش شما ثبت شد و در انتظار پرداخت است.",
  },
  {
    status: "paid",
    label: "پرداخت تأیید شد",
    description: () => "پرداخت با موفقیت انجام شد.",
  },
  {
    status: "processing",
    label: "آماده‌سازی",
    description: () => "سفارش در انبار در حال آماده‌سازی است.",
  },
  {
    status: "shipped",
    label: "تحویل به پست",
    description: (ctx) =>
      ctx.postal_tracking_code
        ? `مرسوله به اداره پست تحویل شد. کد رهگیری پست: ${ctx.postal_tracking_code}`
        : "مرسوله به اداره پست تحویل شد.",
  },
  {
    status: "delivered",
    label: "تحویل به مشتری",
    description: (ctx) =>
      ctx.delivery_eta
        ? `سفارش تحویل داده شد (زمان تحویل: ${new Date(ctx.delivery_eta).toLocaleDateString("fa-IR")}).`
        : "سفارش با موفقیت تحویل داده شد.",
  },
];

const INQUIRY_STAGES: typeof PURCHASE_STAGES = [
  {
    status: "inquiry_review",
    label: "دریافت درخواست",
    description: () => "درخواست استعلام شما دریافت و در صف بررسی قرار گرفت.",
  },
  {
    status: "inquiry_quoted",
    label: "صدور پیش‌فاکتور",
    description: () => "پیش‌فاکتور آماده شد. کارشناسان با شما تماس می‌گیرند.",
  },
  {
    status: "inquiry_closed",
    label: "بستن پرونده",
    description: () => "پرونده استعلام بسته شد.",
  },
];

const STATUS_RANK: Record<OrderStatus, number> = {
  pending_payment: 0,
  paid: 1,
  processing: 2,
  shipped: 3,
  delivered: 4,
  cancelled: 99,
  inquiry_review: 0,
  inquiry_quoted: 1,
  inquiry_closed: 2,
};

export function buildOrderTimeline(ctx: TimelineContext): OrderTrackingEvent[] {
  if (ctx.status === "cancelled") {
    return [
      {
        status: "cancelled",
        status_label: "لغو شده",
        occurred_at: ctx.created_at,
        description: "این سفارش لغو شده است.",
        is_complete: true,
        is_current: true,
      },
    ];
  }

  const stages = ctx.mode === "inquiry" ? INQUIRY_STAGES : PURCHASE_STAGES;
  const currentRank = STATUS_RANK[ctx.status] ?? 0;

  return stages.map((stage, index) => {
    const rank = STATUS_RANK[stage.status] ?? index;
    const isComplete = rank < currentRank || ctx.status === stage.status;
    const isCurrent = ctx.status === stage.status;

    return {
      status: stage.status,
      status_label: stage.label,
      occurred_at: isComplete || isCurrent ? ctx.created_at : "",
      description: isComplete || isCurrent ? stage.description(ctx) : "در انتظار…",
      is_complete: isComplete && !isCurrent ? true : isCurrent,
      is_current: isCurrent,
    };
  });
}
