/** Checkout / order / inquiry payload + response types. */

import type { OrderStatus } from "@/types/order";

export type CheckoutMode = "purchase" | "inquiry";

export interface CheckoutLineInput {
  product_id: number;
  quantity: number;
}

export interface CheckoutCustomer {
  /** Present only for guest checkout; logged-in users are resolved by token. */
  full_name: string;
  phone: string;
  is_guest: boolean;
}

export interface ShippingAddress {
  province: string;
  city: string;
  postal_code: string;
  address_line: string;
}

export interface CheckoutPayload {
  mode: CheckoutMode;
  customer: CheckoutCustomer;
  items: CheckoutLineInput[];
  note?: string | null;
  /** Purchase mode only. */
  shipping?: ShippingAddress;
  /** Inquiry mode only (optional B2B company). */
  company_name?: string | null;
}

export interface CheckoutResponse {
  order_id: number;
  tracking_code: string;
  mode: CheckoutMode;
  status: OrderStatus;
  status_label: string;
  estimated_total: string | null;
  created_at: string;
}
