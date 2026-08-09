/** Format shipping address object as a single Persian-friendly line (decision 5-A). */

export interface ShippingParts {
  province: string;
  city: string;
  postal_code: string;
  address_line: string;
}

export interface BuyerAddressParts {
  /** Province/city + street line only (no postal code). */
  address: string;
  postalCode: string;
}

/** Split saved/checkout shipping into PDF buyer slots (address vs کد پستی). */
export function formatBuyerAddressParts(
  shipping: ShippingParts | Record<string, unknown> | null | undefined,
): BuyerAddressParts {
  if (!shipping || typeof shipping !== "object") {
    return { address: "", postalCode: "" };
  }

  const province = String(shipping.province ?? "").trim();
  const city = String(shipping.city ?? "").trim();
  const postal = String(shipping.postal_code ?? "").trim();
  const line = String(shipping.address_line ?? "").trim();

  const address = [
    province && city ? `${province}، ${city}` : province || city,
    line,
  ]
    .filter(Boolean)
    .join(" — ");

  return { address, postalCode: postal };
}

export function formatShippingAddress(
  shipping: ShippingParts | Record<string, unknown> | null | undefined,
): string | null {
  const { address, postalCode } = formatBuyerAddressParts(shipping);
  const parts = [address, postalCode ? `کد پستی ${postalCode}` : ""].filter(
    Boolean,
  );
  return parts.length ? parts.join(" — ") : null;
}
