/**
 * Verified customer identity boundary for private storefront data (addresses, /me, orders).
 * Works outside React via getCustomerSessionSnapshot / subscribeCustomerSession.
 */

export type CustomerSessionPhase = "unknown" | "checking" | "verified" | "guest";

export type CustomerSessionSnapshot = {
  generation: number;
  phase: CustomerSessionPhase;
  verifiedCustomerId: number | null;
};

/** Captured at the start of an async private operation; publish only while still current. */
export type CustomerSessionFence = {
  generation: number;
  ownerId: number;
};

export const CUSTOMER_SESSION_SIGNAL_KEY = "karzar.customer-session.signal";

const SERVER_SNAPSHOT: CustomerSessionSnapshot = {
  generation: 0,
  phase: "unknown",
  verifiedCustomerId: null,
};

let generation = 1;
let phase: CustomerSessionPhase = "unknown";
let verifiedCustomerId: number | null = null;
/**
 * Soft owner retained across external-hint → checking so same-owner /me recovery
 * does not rebroadcast CUSTOMER_SESSION_SIGNAL_KEY. Never exposed via getters.
 */
let softReverifyOwnerId: number | null = null;

let snapshotCache: CustomerSessionSnapshot = {
  generation,
  phase,
  verifiedCustomerId,
};

const listeners = new Set<() => void>();

export type CustomerSessionHandlers = {
  onSessionInvalidated: (prevOwnerId: number | null) => void;
  onSessionVerified: (ownerId: number, sameOwner: boolean) => void;
};

let handlers: CustomerSessionHandlers | null = null;

function syncSnapshotCache(): void {
  snapshotCache = { generation, phase, verifiedCustomerId };
}

function emit(): void {
  syncSnapshotCache();
  listeners.forEach((l) => l());
}

export function registerCustomerSessionHandlers(next: CustomerSessionHandlers): void {
  handlers = next;
}

export function getCustomerSessionSnapshot(): CustomerSessionSnapshot {
  return snapshotCache;
}

export function subscribeCustomerSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getServerCustomerSessionSnapshot(): CustomerSessionSnapshot {
  return SERVER_SNAPSHOT;
}

export function isPrivateDataEnabled(): boolean {
  return phase === "verified" && verifiedCustomerId != null;
}

export function getVerifiedCustomerId(): number | null {
  return isPrivateDataEnabled() ? verifiedCustomerId : null;
}

/** Discriminator for React Query private cache keys. */
export function getPrivateQueryScope(): readonly [number, number] | readonly ["none", number] {
  if (!isPrivateDataEnabled() || verifiedCustomerId == null) {
    return ["none", generation] as const;
  }
  return [verifiedCustomerId, generation] as const;
}

export function isSessionGenerationCurrent(expectedGeneration: number): boolean {
  return expectedGeneration === generation;
}

export function isSessionOwnerCurrent(
  expectedGeneration: number,
  expectedOwnerId: number,
): boolean {
  return (
    expectedGeneration === generation &&
    phase === "verified" &&
    verifiedCustomerId === expectedOwnerId
  );
}

/** Snapshot verified owner+generation before an async private side effect. */
export function captureVerifiedCustomerSessionFence(): CustomerSessionFence | null {
  if (phase !== "verified" || verifiedCustomerId == null) return null;
  return { generation, ownerId: verifiedCustomerId };
}

export function isCustomerSessionFenceCurrent(fence: CustomerSessionFence | null): boolean {
  if (fence == null) return false;
  return isSessionOwnerCurrent(fence.generation, fence.ownerId);
}

function broadcastCrossTabSignal(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(CUSTOMER_SESSION_SIGNAL_KEY, String(Date.now()));
  } catch {
    /* storage denied */
  }
}

export type InvalidateCustomerSessionOptions = {
  /**
   * When false, do not write CUSTOMER_SESSION_SIGNAL_KEY.
   * Required for transitions driven by an external storage/session hint
   * so tabs cannot rebroadcast and bounce indefinitely.
   */
  broadcast?: boolean;
};

/**
 * Hide private data immediately (logout, account switch, 401, expiry).
 * Does not await network logout — server cookies may remain (F08).
 */
export function invalidateCustomerSession(
  nextPhase: CustomerSessionPhase = "guest",
  options?: InvalidateCustomerSessionOptions,
): void {
  const broadcast = options?.broadcast !== false;
  const prevOwner = verifiedCustomerId;
  generation += 1;
  verifiedCustomerId = null;
  softReverifyOwnerId = null;
  phase = nextPhase;
  handlers?.onSessionInvalidated(prevOwner);
  if (broadcast) {
    broadcastCrossTabSignal();
  }
  emit();
}

export function markCustomerSessionChecking(): void {
  if (phase === "verified" || phase === "checking") return;
  phase = "checking";
  emit();
}

/**
 * Establish verified identity from OTP or successful /me.
 * Same owner + verified → idempotent (no wipe, no broadcast).
 * Same owner recovering from external-hint checking → no cross-tab broadcast.
 */
export function establishVerifiedCustomer(
  customerId: number,
  _source: "otp" | "me" | "profile",
): boolean {
  if (!Number.isFinite(customerId) || customerId <= 0) return false;

  if (phase === "verified" && verifiedCustomerId === customerId) {
    softReverifyOwnerId = null;
    handlers?.onSessionVerified(customerId, true);
    emit();
    return true;
  }

  if (
    phase === "checking" &&
    verifiedCustomerId == null &&
    softReverifyOwnerId === customerId
  ) {
    softReverifyOwnerId = null;
    verifiedCustomerId = customerId;
    phase = "verified";
    handlers?.onSessionVerified(customerId, true);
    emit();
    return true;
  }

  const prevOwner = verifiedCustomerId;
  softReverifyOwnerId = null;
  if (prevOwner != null && prevOwner !== customerId) {
    generation += 1;
    handlers?.onSessionInvalidated(prevOwner);
  }

  verifiedCustomerId = customerId;
  phase = "verified";
  handlers?.onSessionVerified(customerId, false);
  broadcastCrossTabSignal();
  emit();
  return true;
}

/**
 * Another tab changed session-related storage — hide private data and reverify.
 * Must not broadcast CUSTOMER_SESSION_SIGNAL_KEY (receiver-only).
 */
export function notifyExternalSessionHint(): void {
  if (phase === "unknown" || phase === "guest") {
    phase = "checking";
    emit();
    return;
  }

  const prevOwner = verifiedCustomerId;
  softReverifyOwnerId = prevOwner ?? softReverifyOwnerId;
  generation += 1;
  verifiedCustomerId = null;
  phase = "checking";
  handlers?.onSessionInvalidated(prevOwner);
  emit();
}

export function markCustomerSessionGuest(): void {
  if (phase === "guest" && verifiedCustomerId == null) return;
  invalidateCustomerSession("guest");
}

/** Test-only reset — not for production use. */
export function resetCustomerSessionStateForTests(): void {
  generation = 1;
  phase = "unknown";
  verifiedCustomerId = null;
  softReverifyOwnerId = null;
  syncSnapshotCache();
  listeners.clear();
}
