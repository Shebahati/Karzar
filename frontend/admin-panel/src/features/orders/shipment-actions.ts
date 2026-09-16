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
  fulfillment_mode?: string | null;
  registration_source?: string | null;
}

export type HazardChoice = null | boolean;

export function canSubmitFinalPackageHazards(
  isFragile: HazardChoice,
  isLiquid: HazardChoice,
): boolean {
  return isFragile !== null && isLiquid !== null;
}

export function manualPortalStatusLabel(shipment: AdminShipment): string | null {
  if (shipment.fulfillment_mode !== "manual_portal") {
    return null;
  }
  if (shipment.status === "awaiting_packaging" && !shipment.tracking_code) {
    return "در انتظار ثبت دستی در پنل پستکس";
  }
  return null;
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
    carrierCode: primary?.carrier_code ?? order.shipping_carrier_code ?? null,
    serviceCode: primary?.service_code ?? order.shipping_service_code ?? null,
    providerQuotedCost:
      primary?.provider_quoted_cost ?? order.shipping_provider_quoted_cost ?? null,
  };
}

const MANUAL_PROVIDERS = new Set(["tipax", "chapar", "iran_post", "local_delivery"]);

export function isManualFulfillmentProvider(provider: string | null | undefined): boolean {
  return MANUAL_PROVIDERS.has((provider || "").trim());
}

/** Legacy Postex API quote/book UI — not storefront matrix carriers. */
export function usesPostexAutomationUi(shipment: AdminShipment): boolean {
  if (shipment.fulfillment_mode === "manual_portal") {
    return false;
  }
  return (shipment.provider || "").trim() === "postex";
}

export function shipmentActionAvailability(
  shipment: AdminShipment,
  orderStatus?: string | null,
) {
  const order = (orderStatus || "").trim().toLowerCase();
  const manual = isManualFulfillmentProvider(shipment.provider);
  const postexAutomation = usesPostexAutomationUi(shipment);
  const booked = Boolean(shipment.provider_parcel_no);
  const terminal = shipment.status === "delivered" || shipment.status === "cancelled";
  const receiverDue = shipment.shipping_payment_mode === "receiver_due";
  const manualPortal =
    shipment.fulfillment_mode === "manual_portal" ||
    shipment.registration_source === "manual_portal";
  const manualRegistered = shipment.registration_source === "manual_portal" || booked;
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

  if (manualPortal && receiverDue) {
    return {
      canSetPackage: false,
      canPackedQuote: false,
      canSelectService: false,
      canScheduleBooking: false,
      canBook: false,
      canReady: false,
      canLabel: false,
      canRefresh: false,
      canEdit: false,
      canCancel: false,
      canRetrySafe: false,
      canManualRegister:
        shipment.status === "awaiting_packaging" && !shipment.tracking_code && !manualRegistered,
      canManualHandoff: manualRegistered && shipment.status === "booked",
      canManualDeliver: shipment.status === "picked_up",
      canManualCorrect:
        manualRegistered &&
        shipment.status === "booked" &&
        shipment.registration_source === "manual_portal",
      canManualAbandon: false,
    };
  }

  const handoffShipmentOk = shipment.status === "booked";
  const deliverShipmentOk =
    shipment.status === "picked_up" ||
    shipment.status === "in_transit" ||
    shipment.status === "out_for_delivery";

  return {
    canManualRegister: manual && shipment.status === "awaiting_packaging",
    canManualHandoff:
      manual && handoffShipmentOk && order === "processing",
    canManualDeliver: manual && deliverShipmentOk && order === "shipped",
    canSetPackage: postexAutomation && preCreate && !booked,
    canPackedQuote:
      postexAutomation &&
      receiverDue &&
      packaged &&
      (shipment.status === "awaiting_packaging" || shipment.status === "ready_to_book"),
    canSelectService:
      postexAutomation &&
      receiverDue &&
      packaged &&
      (shipment.status === "awaiting_packaging" || shipment.status === "ready_to_book"),
    canScheduleBooking:
      postexAutomation &&
      receiverDue &&
      packaged &&
      serviceSelected &&
      Boolean(shipment.package?.provider_box_type_id) &&
      shipment.status === "awaiting_packaging",
    canBook:
      postexAutomation &&
      (shipment.status === "ready_to_book" ||
        shipment.status === "pending_booking" ||
        shipment.status === "error" ||
        shipment.status === "creation_uncertain"),
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
    canManualCorrect: false,
    canManualAbandon: false,
  };
}
