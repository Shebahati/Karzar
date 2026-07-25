import { describe, expect, it } from "vitest";

import {
  getPrimaryAction,
  getWorkflowSteps,
  validateStatusTransition,
} from "@/features/orders/order-workflow";
import type { OrderDetail } from "@/types/order";

const purchaseOrder = (status: OrderDetail["status"]): OrderDetail =>
  ({
    id: 1,
    mode: "purchase",
    status,
  }) as OrderDetail;

const inquiryOrder = (status: OrderDetail["status"]): OrderDetail =>
  ({
    id: 2,
    mode: "inquiry",
    status,
  }) as OrderDetail;

describe("order-workflow", () => {
  it("returns purchase steps for purchase orders", () => {
    expect(getWorkflowSteps({ mode: "purchase" })).toEqual([
      "pending_payment",
      "paid",
      "processing",
      "shipped",
      "delivered",
    ]);
  });

  it("maps primary advance action to the next status", () => {
    const action = getPrimaryAction(purchaseOrder("paid"));
    expect(action?.nextStatus).toBe("processing");
    expect(validateStatusTransition(purchaseOrder("paid"), "processing")).toBeNull();
  });

  it("rejects invalid transitions", () => {
    expect(validateStatusTransition(purchaseOrder("paid"), "shipped")).toMatch(
      /مسیر مجاز/,
    );
  });

  it("allows inquiry quote flow", () => {
    const action = getPrimaryAction(inquiryOrder("inquiry_review"));
    expect(action?.type).toBe("quote");
    expect(action?.nextStatus).toBe("inquiry_quoted");
    expect(
      validateStatusTransition(inquiryOrder("inquiry_review"), "inquiry_quoted"),
    ).toBeNull();
  });

  it("always allows cancel transition", () => {
    expect(validateStatusTransition(purchaseOrder("processing"), "cancelled")).toBeNull();
  });
});
