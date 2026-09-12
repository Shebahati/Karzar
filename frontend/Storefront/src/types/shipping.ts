export interface ShippingStatus {
  enabled: boolean;
  quote_ttl_seconds: number;
  /** Provider-neutral: sender_prepaid | receiver_due */
  shipping_payment_mode?: string | null;
  /** False for receiver_due — do not call /shipping/quotes at checkout. */
  checkout_quote_required?: boolean;
  booking_enabled?: boolean;
}

export interface ShippingCity {
  code: number;
  name: string;
  province_code: number | null;
  province_name: string | null;
}

export interface ShippingQuoteOption {
  quote_token: string;
  carrier_code: string;
  service_code: string;
  title: string;
  amount_toman: string;
  eta: string | null;
  expires_at: string;
}

export interface ShippingQuoteResponse {
  quote_group_id: string;
  expires_at: string;
  options: ShippingQuoteOption[];
}

export interface PublicShipmentEvent {
  status: string;
  status_label: string;
  provider_status?: string | null;
  occurred_at?: string | null;
  description?: string | null;
}

export interface PublicShipment {
  id: string;
  status: string;
  status_label: string;
  carrier_code?: string | null;
  service_code?: string | null;
  service_name?: string | null;
  tracking_code?: string | null;
  shipped_at?: string | null;
  delivered_at?: string | null;
  events: PublicShipmentEvent[];
}
