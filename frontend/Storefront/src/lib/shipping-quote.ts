export function payableTotalToman(itemsSubtotal: number, shippingToman: number | null): number {
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
}): boolean {
  if (!params.postexEnabled) return true;
  if (params.shippingUnavailable) return false;
  if (!params.quoteToken) return false;
  return !isQuoteExpired(params.expiresAt);
}
