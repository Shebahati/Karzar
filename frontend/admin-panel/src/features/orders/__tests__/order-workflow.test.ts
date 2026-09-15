import { describe, expect, it } from "vitest";

import {
  getPrimaryAction,
  orderHasActiveManualPortalFulfillment,
} from "@/features/orders/order-workflow";
import type { OrderDetail } from "@/types/order";

function order(partial: Partial<OrderDetail>): OrderDetail {
  return {
    id: 1,
    tracking_code: "KZ-TEST",
    mode: "purchase",
    status: "paid",
    shipments: [],
    ...partial,
  } as OrderDetail;
}

describe("order-workflow manual portal guards", () => {
  it("detects active manual portal shipments", () => {
    expect(
      orderHasActiveManualPortalFulfillment(
        order({
          shipments: [{ fulfillment_mode: "manual_portal", status: "booked" } as never],
        }),
      ),
    ).toBe(true);
  });

  it("keeps paid→processing primary action for manual portal orders", () => {
    const action = getPrimaryAction(
      order({
        status: "paid",
        shipments: [{ fulfillment_mode: "manual_portal", status: "booked" } as never],
      }),
    );
    expect(action?.nextStatus).toBe("processing");
  });

  it("hides generic ship/deliver actions when manual portal is active", () => {
    expect(
      getPrimaryAction(
        order({
          status: "processing",
          shipments: [{ fulfillment_mode: "manual_portal", status: "booked" } as never],
        }),
      ),
    ).toBeNull();
    expect(
      getPrimaryAction(
        order({
          status: "shipped",
          shipments: [{ fulfillment_mode: "manual_portal", status: "picked_up" } as never],
        }),
      ),
    ).toBeNull();
  });
});
