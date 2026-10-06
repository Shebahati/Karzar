import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  CUSTOMER_SESSION_SIGNAL_KEY,
  establishVerifiedCustomer,
  getCustomerSessionSnapshot,
  getPrivateQueryScope,
  getVerifiedCustomerId,
  invalidateCustomerSession,
  isPrivateDataEnabled,
  isSessionOwnerCurrent,
  notifyExternalSessionHint,
  resetCustomerSessionStateForTests,
  captureVerifiedCustomerSessionFence,
  isCustomerSessionFenceCurrent,
} from "@/lib/customer-session";

describe("customer-session boundary", () => {
  beforeEach(() => {
    resetCustomerSessionStateForTests();
    localStorage.clear();
    vi.restoreAllMocks();
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

  it("T06: fence is current only for same verified owner+generation", () => {
    establishVerifiedCustomer(7, "otp");
    const fence = captureVerifiedCustomerSessionFence();
    expect(isCustomerSessionFenceCurrent(fence)).toBe(true);
    invalidateCustomerSession("guest");
    expect(isCustomerSessionFenceCurrent(fence)).toBe(false);
    expect(captureVerifiedCustomerSessionFence()).toBeNull();
  });

  it("T11: notifyExternalSessionHint must not write CUSTOMER_SESSION_SIGNAL_KEY", () => {
    establishVerifiedCustomer(11, "otp");
    localStorage.removeItem(CUSTOMER_SESSION_SIGNAL_KEY);
    const genBefore = getCustomerSessionSnapshot().generation;

    notifyExternalSessionHint();

    expect(getCustomerSessionSnapshot().phase).toBe("checking");
    expect(getCustomerSessionSnapshot().verifiedCustomerId).toBeNull();
    expect(getCustomerSessionSnapshot().generation).toBeGreaterThan(genBefore);
    expect(isPrivateDataEnabled()).toBe(false);
    expect(localStorage.getItem(CUSTOMER_SESSION_SIGNAL_KEY)).toBeNull();

    // Same-owner recovery from soft reverify hint must also avoid broadcast.
    establishVerifiedCustomer(11, "me");
    expect(getVerifiedCustomerId()).toBe(11);
    expect(localStorage.getItem(CUSTOMER_SESSION_SIGNAL_KEY)).toBeNull();
  });

  it("T11: local invalidateCustomerSession still broadcasts by default", () => {
    establishVerifiedCustomer(12, "otp");
    localStorage.removeItem(CUSTOMER_SESSION_SIGNAL_KEY);
    invalidateCustomerSession("guest");
    expect(localStorage.getItem(CUSTOMER_SESSION_SIGNAL_KEY)).not.toBeNull();
  });

  it("T11: invalidateCustomerSession({ broadcast: false }) is silent", () => {
    establishVerifiedCustomer(13, "otp");
    localStorage.removeItem(CUSTOMER_SESSION_SIGNAL_KEY);
    invalidateCustomerSession("guest", { broadcast: false });
    expect(localStorage.getItem(CUSTOMER_SESSION_SIGNAL_KEY)).toBeNull();
  });
});
