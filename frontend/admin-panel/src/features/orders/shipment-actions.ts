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
  shipping_payment_mode?: string | null;
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
    is_fragile?: boolean | null;
    is_liquid?: boolean | null;
    measured_at?: string | null;
    provider_box_type_id?: number | null;
  } | null;
  customer_shipping_cost?: string | null;
  provider_quoted_cost?: string | null;
  provider_quoted_at?: string | null;
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

export type HazardChoice = null | boolean;

export function canSubmitFinalPackageHazards(
  isFragile: HazardChoice,
  isLiquid: HazardChoice,
): boolean {
  return isFragile !== null && isLiquid !== null;
}

/** Operational carrier/service/quote for receiver_due live on Shipment, not Order checkout snapshot. */
export function receiverFulfillmentDisplay(
  order: {
    shipping_carrier_code?: string | null;
    shipping_service_code?: string | null;
    shipping_provider_quoted_cost?: string | null;
  },
  shipments: AdminShipment[],
) {
  const primary = shipments[0];
  return {
    carrierCode: order.shipping_carrier_code ?? primary?.carrier_code ?? null,
    serviceCode: order.shipping_service_code ?? primary?.service_code ?? null,
    providerQuotedCost:
      order.shipping_provider_quoted_cost ?? primary?.provider_quoted_cost ?? null,
  };
}

export function shipmentActionAvailability(shipment: AdminShipment) {
  const booked = Boolean(shipment.provider_parcel_no);
  const terminal = shipment.status === "delivered" || shipment.status === "cancelled";
  const receiverDue = shipment.shipping_payment_mode === "receiver_due";
  const packaged =
    (shipment.package?.length_cm ?? 0) > 0 &&
    (shipment.package?.weight_grams ?? 0) > 0 &&
    shipment.package?.is_fragile != null &&
    shipment.package?.is_liquid != null;
  const serviceSelected = Boolean(shipment.carrier_code && shipment.service_code);
  const preCreate =
    shipment.status === "awaiting_packaging" ||
    shipment.status === "ready_to_book" ||
    shipment.status === "freight_required";
  return {
    canSetPackage: preCreate && !booked,
    canPackedQuote:
      receiverDue &&
      packaged &&
      (shipment.status === "awaiting_packaging" || shipment.status === "ready_to_book"),
    canSelectService:
      receiverDue &&
      packaged &&
      (shipment.status === "awaiting_packaging" || shipment.status === "ready_to_book"),
    canScheduleBooking:
      receiverDue &&
      packaged &&
      serviceSelected &&
      Boolean(shipment.package?.provider_box_type_id) &&
      shipment.status === "awaiting_packaging",
    canBook:
      shipment.status === "ready_to_book" ||
      shipment.status === "pending_booking" ||
      shipment.status === "error" ||
      shipment.status === "creation_uncertain",
    canReady:
      booked &&
      (shipment.status === "booked" || shipment.status === "ready_for_pickup") &&
      !shipment.ready_to_accept,
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
