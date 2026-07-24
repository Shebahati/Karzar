/** Payment gateway types. Amounts are in Tomans. Backend-aligned (decision 13-A). */

import type { OrderStatus } from "@/types/order";

export interface PaymentInitPayload {
  order_id: number;
}

/** Backend POST /payments/init response */
export interface PaymentInitBackendResponse {
  authority: string;
  payment_url: string;
}

export interface PaymentInitResponse {
  authority: string;
  payment_url: string;
}

export interface PaymentVerifyPayload {
  /** Optional — server resolves order from authority when omitted. */
  order_id?: number;
  authority: string;
  status?: string;
  /** Filled by FE from pending payment / recovery — not sent to backend. */
  tracking_code?: string;
}

/** Backend POST /payments/verify response */
export interface PaymentVerifyBackendResponse {
  order_id: number;
  payment_status: string;
  status: OrderStatus;
  ref_id: string | null;
  tracking_code?: string | null;
}

export interface PaymentVerifyResponse {
  success: boolean;
  order_id: number;
  tracking_code: string;
  status: OrderStatus;
  status_label: string;
  ref_id: string | null;
  message: string;
}
