/**
 * Cart proforma preview (UI login-gated in CartProformaButton).
 *
 * As-built OpenAPI: only admin `POST /orders/{order_id}/quote` exists (auth +
 * existing inquiry order). There is no public cart preview endpoint, so the
 * storefront opens a labelled sample پیش‌فاکتور via HTML print (IRANYekanX /
 * UTF-8) — not jsPDF — to avoid Persian mojibake.
 *
 * When a public preview endpoint is added (e.g. blob/PDF response for cart
 * lines), call it here first and fall back to the local sample on failure —
 * without inventing request fields.
 */
import {
  downloadCartSampleProforma,
  type CartProformaBuyer,
  type CartProformaLineInput,
} from "@/lib/invoice-pdf";
import type { CartLine } from "@/store/cart-store";

export function cartLinesToProformaInput(lines: CartLine[]): CartProformaLineInput[] {
  return lines.map((line) => ({
    productId: line.product.id,
    name: line.product.name,
    sku: line.product.sku,
    quantity: line.quantity,
    unitPrice: line.product.base_price,
  }));
}

/** Open sample (or future live) cart proforma — caller enforces login + customer name. */
export async function downloadGuestCartProforma(
  lines: CartLine[],
  buyer: CartProformaBuyer,
): Promise<void> {
  // Future: try live public preview when documented in OpenAPI, then fall back.
  await downloadCartSampleProforma(cartLinesToProformaInput(lines), buyer);
}
