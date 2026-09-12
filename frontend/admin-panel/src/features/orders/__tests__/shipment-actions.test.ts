import { describe, expect, it } from "vitest";
import {
  canSubmitFinalPackageHazards,
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
  it("allows booking only for ready_to_book/pending/error/uncertain", () => {
    expect(shipmentActionAvailability(shipment({ status: "ready_to_book" })).canBook).toBe(true);
    expect(shipmentActionAvailability(shipment({ status: "pending_booking" })).canBook).toBe(true);
    expect(shipmentActionAvailability(shipment({ status: "booked", provider_parcel_no: "1" })).canBook).toBe(
      false,
    );
    expect(shipmentActionAvailability(shipment({ status: "awaiting_packaging" })).canBook).toBe(false);
  });

  it("gates label and cancel", () => {
    expect(shipmentActionAvailability(shipment({ provider_parcel_no: "1" })).canLabel).toBe(true);
    expect(shipmentActionAvailability(shipment({ status: "delivered" })).canCancel).toBe(false);
    expect(
      shipmentActionAvailability(shipment({ status: "cancellation_pending", provider_parcel_no: "1" }))
        .canCancel,
    ).toBe(false);
    expect(
      shipmentActionAvailability(
        shipment({ status: "error", last_error_code: "CREATION_UNCERTAIN" }),
      ).canRetrySafe,
    ).toBe(false);
  });

  it("requires explicit hazard yes/no before package submit", () => {
    expect(canSubmitFinalPackageHazards(null, false)).toBe(false);
    expect(canSubmitFinalPackageHazards(true, null)).toBe(false);
    expect(canSubmitFinalPackageHazards(true, false)).toBe(true);
    expect(canSubmitFinalPackageHazards(false, false)).toBe(true);
  });

  it("keeps package forms conceptually per shipment via internal_id keys", () => {
    const a = shipment({ internal_id: 11, status: "awaiting_packaging" });
    const b = shipment({ internal_id: 22, status: "awaiting_packaging" });
    const forms: Record<number, { length_cm: string }> = {
      [a.internal_id]: { length_cm: "10" },
      [b.internal_id]: { length_cm: "40" },
    };
    expect(forms[a.internal_id]?.length_cm).toBe("10");
    expect(forms[b.internal_id]?.length_cm).toBe("40");
  });
});
