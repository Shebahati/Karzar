/** Order status enum — aligned with backend commerce.OrderStatus (decision 13-A). */

export const ORDER_STATUSES = [
  "pending_payment",
  "paid",
  "processing",
  "shipped",
  "delivered",
  "cancelled",
  "inquiry_review",
  "inquiry_quoted",
  "inquiry_closed",
] as const;

export type OrderStatus = (typeof ORDER_STATUSES)[number];

export interface OrderSummary {
  id: number;
  tracking_code: string;
  status: OrderStatus;
  status_label: string;
  mode: "purchase" | "inquiry";
  estimated_total: string | null;
  created_at: string;
}

export interface OrderLineItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: string | null;
  line_total: string | null;
}

export interface OrderDetail extends OrderSummary {
  customer_name: string;
  customer_phone: string;
  shipping_address: string | null;
  note: string | null;
  payment_status: string | null;
  items: OrderLineItem[];
}

export interface OrderTrackingEvent {
  status: OrderStatus;
  status_label: string;
  occurred_at: string;
  description: string | null;
  /** UI hints for rich timeline (decision 6-B). */
  is_complete?: boolean;
  is_current?: boolean;
}

export interface OrderTrackingItem {
  product_id: number;
  quantity: number;
  unit_price: string | null;
}

export interface OrderTracking {
  tracking_code: string;
  status: OrderStatus;
  status_label: string;
  mode: "purchase" | "inquiry";
  /** Not present on public tracking API — kept optional for UI compatibility. */
  estimated_total: string | null;
  created_at: string;
  postal_tracking_code?: string | null;
  delivery_eta?: string | null;
  items?: OrderTrackingItem[];
  timeline: OrderTrackingEvent[];
  /** True when timeline was inferred client-side via buildOrderTimeline (not server history). */
  timeline_estimated?: boolean;
}

export interface OrderListResponse {
  data: OrderSummary[];
  meta: import("@/types/common").PaginationMeta;
}
