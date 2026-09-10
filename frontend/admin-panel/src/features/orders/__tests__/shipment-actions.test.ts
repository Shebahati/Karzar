import { describe, expect, it } from "vitest";
import {
  shipmentActionAvailability,
  type AdminShipment,
} from "@/features/orders/shipment-actions";

function shipment(patch: Partial<AdminShipment>): AdminShipment {
  return {
    id: "pub",
    internal_id: 1,
    status: "booked",
    status_label: "ثبت شد",
    provider: "postex",
    events: [],
    ...patch,
  };
}

describe("shipmentActionAvailability", () => {
  it("allows booking only for pending/error/uncertain", () => {
    expect(shipmentActionAvailability(shipment({ status: "pending_booking" })).canBook).toBe(true);
    expect(shipmentActionAvailability(shipment({ status: "booked", provider_parcel_no: "1" })).canBook).toBe(
      false,
    );
  });

  it("gates label and cancel", () => {
    expect(shipmentActionAvailability(shipment({ provider_parcel_no: "1" })).canLabel).toBe(true);
    expect(shipmentActionAvailability(shipment({ status: "delivered" })).canCancel).toBe(false);
    expect(
      shipmentActionAvailability(
        shipment({ status: "error", last_error_code: "CREATION_UNCERTAIN" }),
      ).canRetrySafe,
    ).toBe(false);
  });
});
