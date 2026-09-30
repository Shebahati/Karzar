/**
 * Entity lookup error helpers for App Router pages.
 *
 * Distinguishes API/mock "not found" from upstream failures so routes can:
 * - notFound() → HTTP 404 for missing entities
 * - rethrow → error boundary for 5xx/network
 * Never substitute mock/demo content for a real-mode miss.
 */

import { notFound, unstable_rethrow } from "next/navigation";
import { ApiError } from "@/lib/api-client";

/** True when the failure means the entity does not exist (not an outage). */
export function isEntityNotFoundError(error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.status === 404;
  }
  if (error instanceof Error) {
    return /یافت نشد|not found/i.test(error.message);
  }
  return false;
}

/**
 * Rethrow Next.js control-flow errors, convert entity-miss to `notFound()`,
 * otherwise propagate upstream failures unchanged.
 */
export function rejectUnlessEntityNotFound(error: unknown): never {
  unstable_rethrow(error);
  if (isEntityNotFoundError(error)) {
    notFound();
  }
  throw error;
}
