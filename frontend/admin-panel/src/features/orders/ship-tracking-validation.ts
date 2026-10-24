/** Shared validation for admin shipment tracking codes (string-safe, preserves leading zeros). */

export const MIN_POSTAL_TRACKING_LENGTH = 10;

export function normalizeTrackingCodeInput(raw: string): string {
  return raw.trim();
}

export function isValidPostalTrackingCode(raw: string): boolean {
  const code = normalizeTrackingCodeInput(raw);
  return code.length >= MIN_POSTAL_TRACKING_LENGTH;
}
