export interface AdminShipmentEvent {
  status: string;
  status_label: string;
  provider_status?: string | null;
  occurred_at?: string | null;
  description?: string | null;
}

export interface AdminShipment {
  id: string;
  internal_id: number;
  status: string;
  status_label: string;
  provider: string;
  carrier_code?: string | null;
  service_code?: string | null;
  service_name?: string | null;
  tracking_code?: string | null;
  provider_parcel_no?: string | null;
  quote_id?: number | null;
  package?: {
    length_cm?: number | null;
    width_cm?: number | null;
    height_cm?: number | null;
    weight_grams?: number | null;
  } | null;
  customer_shipping_cost?: string | null;
  provider_quoted_cost?: string | null;
  provider_actual_cost?: string | null;
  ready_to_accept?: boolean;
  booking_attempts?: number;
  last_tracking_sync_at?: string | null;
  last_error_code?: string | null;
  last_error_message?: string | null;
  shipped_at?: string | null;
  delivered_at?: string | null;
  events: AdminShipmentEvent[];
}

export function shipmentActionAvailability(shipment: AdminShipment) {
  const booked = Boolean(shipment.provider_parcel_no);
  const terminal = shipment.status === "delivered" || shipment.status === "cancelled";
  return {
    canBook:
      shipment.status === "pending_booking" ||
      shipment.status === "error" ||
      shipment.status === "creation_uncertain",
    canReady: booked && (shipment.status === "booked" || shipment.status === "ready_for_pickup") && !shipment.ready_to_accept,
    canLabel: booked,
    canRefresh: booked,
    canEdit: booked && (shipment.status === "booked" || shipment.status === "ready_for_pickup"),
    canCancel:
      !terminal &&
      shipment.status !== "returned" &&
      shipment.status !== "cancellation_pending",
    canRetrySafe: shipment.status === "error" && shipment.last_error_code !== "CREATION_UNCERTAIN",
  };
}
