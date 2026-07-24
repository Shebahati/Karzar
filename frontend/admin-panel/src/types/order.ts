/** Order types for admin panel — backend-aligned (decision 13-A). */

import type { PaginatedResponse } from "./common";

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
  customer_name: string;
  customer_phone: string;
  estimated_total: string | null;
  created_at: string;
}

/** Raw line item from backend (no product name/sku). */
export interface OrderLineItemRaw {
  id?: number;
  product_id: number;
  quantity: number;
  unit_price: string | null;
}

export interface OrderLineItem extends OrderLineItemRaw {
  product_name: string;
  sku: string | null;
  line_total: string | null;
}

export interface OrderInvoice {
  invoice_number: string;
  issued_at: string;
  valid_until: string | null;
  total: string;
  note: string | null;
}

export interface OrderTimelineEvent {
  status: OrderStatus;
  status_label: string;
  occurred_at: string;
  description: string;
  actor?: "system" | "admin";
}

export interface OrderDetail extends OrderSummary {
  note: string | null;
  shipping_address: string | null;
  payment_status: string | null;
  items: OrderLineItem[];
  postal_tracking_code?: string | null;
  delivery_eta?: string | null;
  invoice?: OrderInvoice | null;
  timeline?: OrderTimelineEvent[];
}

export interface IssueQuotePayload {
  items: Array<{ product_id: number; unit_price: string; quantity: number }>;
  note?: string | null;
  valid_until?: string | null;
}

export type OrderListResponse = PaginatedResponse<OrderSummary>;

export interface OrderListParams {
  skip?: number;
  limit?: number;
  status?: OrderStatus;
  search?: string;
  mode?: "purchase" | "inquiry";
  customer_phone?: string;
}

export interface OrderStatusUpdatePayload {
  status: OrderStatus;
  note?: string | null;
  postal_tracking_code?: string | null;
  delivery_eta?: string | null;
}

export interface OrderDetailBackend {
  id: number;
  tracking_code: string;
  status: OrderStatus;
  status_label: string;
  mode: "purchase" | "inquiry";
  customer_full_name: string;
  customer_phone: string;
  estimated_total: string | null;
  created_at: string;
  note: string | null;
  shipping: Record<string, unknown> | null;
  payment_status: string;
  items: OrderLineItemRaw[];
  postal_tracking_code?: string | null;
  delivery_eta?: string | null;
  invoice?: OrderInvoice | null;
  timeline?: OrderTimelineEvent[];
}
