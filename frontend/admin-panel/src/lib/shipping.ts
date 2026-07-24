export interface ShippingParts {
  province: string;
  city: string;
  postal_code: string;
  address_line: string;
}

export function formatShippingAddress(
  shipping: ShippingParts | Record<string, unknown> | null | undefined,
): string | null {
  if (!shipping || typeof shipping !== "object") return null;

  const province = String(shipping.province ?? "").trim();
  const city = String(shipping.city ?? "").trim();
  const postal = String(shipping.postal_code ?? "").trim();
  const line = String(shipping.address_line ?? "").trim();

  const parts = [
    province && city ? `${province}، ${city}` : province || city,
    line,
    postal ? `کد پستی ${postal}` : "",
  ].filter(Boolean);

  return parts.length ? parts.join(" — ") : null;
}
