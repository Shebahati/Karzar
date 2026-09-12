export function payableTotalToman(
  itemsSubtotal: number,
  shippingToman: number | null,
  opts?: { shippingExcluded?: boolean },
): number {
  if (opts?.shippingExcluded) return itemsSubtotal;
  return itemsSubtotal + (shippingToman ?? 0);
}

export function isQuoteExpired(expiresAt: string | null | undefined, now = Date.now()): boolean {
  if (!expiresAt) return true;
  const ts = Date.parse(expiresAt);
  if (Number.isNaN(ts)) return true;
  return ts <= now;
}

export function canSubmitPurchaseShipping(params: {
  postexEnabled: boolean;
  quoteToken: string | null;
  expiresAt: string | null;
  shippingUnavailable: boolean;
  /** When true (receiver_due / پس‌کرایه), quote token is not required. */
  checkoutQuoteRequired?: boolean;
  locationCode?: number | null;
}): boolean {
  if (!params.postexEnabled) return true;
  if (params.shippingUnavailable) return false;
  const quoteRequired = params.checkoutQuoteRequired !== false;
  if (!quoteRequired) {
    return params.locationCode != null && params.locationCode > 0;
  }
  if (!params.quoteToken) return false;
  return !isQuoteExpired(params.expiresAt);
}
