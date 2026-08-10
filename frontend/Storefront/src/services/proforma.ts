/**
 * Cart proforma (UI login-gated in CartProformaButton).
 *
 * As-built OpenAPI: only admin `POST /orders/{order_id}/quote` exists (auth +
 * existing inquiry order). There is no public cart quote endpoint, so the
 * storefront opens a numbered پیش‌فاکتور via HTML print (IRANYekanX / UTF-8)
 * — not jsPDF — to avoid Persian mojibake.
 *
 * When a public quote endpoint is added (e.g. blob/PDF response for cart
 * lines), call it here first and fall back to the local document on failure —
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
    originalPrice: line.product.original_price ?? null,
    discountPercent: line.product.discount_percent ?? null,
  }));
}

/** Open cart proforma with a real PF number — caller enforces login + customer name. */
export async function downloadGuestCartProforma(
  lines: CartLine[],
  buyer: CartProformaBuyer,
): Promise<void> {
  // Future: try live public quote when documented in OpenAPI, then fall back.
  await downloadCartSampleProforma(cartLinesToProformaInput(lines), buyer);
}
