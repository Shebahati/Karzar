import { beforeEach, describe, expect, it } from "vitest";
import {
  establishVerifiedCustomer,
  getCustomerSessionSnapshot,
  getPrivateQueryScope,
  getVerifiedCustomerId,
  invalidateCustomerSession,
  isPrivateDataEnabled,
  isSessionOwnerCurrent,
  resetCustomerSessionStateForTests,
} from "@/lib/customer-session";

describe("customer-session boundary", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
  });

  it("T08: exposes no verified owner until established", () => {
    expect(getVerifiedCustomerId()).toBeNull();
    expect(isPrivateDataEnabled()).toBe(false);
    expect(getPrivateQueryScope()).toEqual(["none", 1]);
  });

  it("T05/T07: generation bumps on invalidate and guards late owner work", () => {
    establishVerifiedCustomer(10, "otp");
    const gen = getCustomerSessionSnapshot().generation;
    invalidateCustomerSession("guest");
    expect(isSessionOwnerCurrent(gen, 10)).toBe(false);
    establishVerifiedCustomer(20, "otp");
    expect(getVerifiedCustomerId()).toBe(20);
    expect(getPrivateQueryScope()[0]).toBe(20);
  });

  it("T12: same-owner establish is idempotent (no generation bump)", () => {
    establishVerifiedCustomer(3, "otp");
    const gen = getCustomerSessionSnapshot().generation;
    establishVerifiedCustomer(3, "me");
    expect(getCustomerSessionSnapshot().generation).toBe(gen);
    expect(getVerifiedCustomerId()).toBe(3);
  });

  it("T01: account switch bumps generation between A and B", () => {
    establishVerifiedCustomer(1, "otp");
    const genA = getCustomerSessionSnapshot().generation;
    establishVerifiedCustomer(2, "otp");
    expect(getCustomerSessionSnapshot().generation).toBeGreaterThan(genA);
    expect(getVerifiedCustomerId()).toBe(2);
  });
});
