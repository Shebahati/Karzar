/**
 * Authenticated order invoice / proforma download.
 * Orchestrates track + catalog name enrichment + shared HTML renderer.
 */
import { catalogService } from "@/services/catalog";
import { orderService } from "@/services/orders";
import {
  downloadOrderPdf,
  type DownloadOrderPdfOptions,
  type InvoiceProductHint,
} from "@/lib/invoice-pdf";
import type { OrderSummary, OrderTracking } from "@/types/order";

function resolveKind(
  order: Pick<OrderSummary, "mode">,
  kind?: "invoice" | "proforma",
): "invoice" | "proforma" {
  if (kind) return kind;
  return order.mode === "inquiry" ? "proforma" : "invoice";
}

async function enrichProducts(
  tracking: OrderTracking,
): Promise<Record<number, InvoiceProductHint>> {
  const ids = (tracking.items ?? []).map((item) => item.product_id);
  if (ids.length === 0) return {};
  try {
    const products = await catalogService.getProductsByIds(ids);
    return Object.fromEntries(
      products.map((p) => [
        p.id,
        {
          name: p.name,
          sku: p.sku,
          originalPrice: p.original_price ?? null,
          discountPercent: p.discount_percent ?? null,
        },
      ]),
    );
  } catch {
    return {};
  }
}

function optionsFromSummary(
  order: OrderSummary,
  kind: "invoice" | "proforma",
  products: Record<number, InvoiceProductHint>,
  tracking: OrderTracking,
): DownloadOrderPdfOptions {
  return {
    kind,
    buyerName: order.customer_full_name ?? null,
    buyerPhone: order.customer_phone ?? null,
    // Shipping address is not on `/orders/me` or public track — leave blank.
    buyerAddress: null,
    companyName: order.company_name ?? null,
    paymentStatusLabel: order.payment_status_label ?? null,
    estimatedTotal: tracking.estimated_total ?? order.estimated_total,
    products,
  };
}

/** Download فاکتور خرید / پیش‌فاکتور for a listed account order. */
export async function downloadAccountOrderDocument(
  order: OrderSummary,
  kind?: "invoice" | "proforma",
): Promise<void> {
  const resolved = resolveKind(order, kind);
  const tracking = await orderService.track(order.tracking_code);
  const products = await enrichProducts(tracking);
  await downloadOrderPdf(
    tracking,
    optionsFromSummary(order, resolved, products, tracking),
  );
}

/**
 * Download from order detail when tracking (+ optional list summary / product map)
 * is already loaded — avoids a second track round-trip when possible.
 */
export async function downloadOrderDocumentFromTracking(
  tracking: OrderTracking,
  extras: {
    summary?: OrderSummary | null;
    products?: Record<number, InvoiceProductHint>;
    kind?: "invoice" | "proforma";
  } = {},
): Promise<void> {
  const kind =
    extras.kind ??
    (tracking.mode === "inquiry" ? "proforma" : "invoice");

  const products =
    extras.products && Object.keys(extras.products).length > 0
      ? extras.products
      : await enrichProducts(tracking);

  const summary = extras.summary;
  await downloadOrderPdf(tracking, {
    kind,
    buyerName: summary?.customer_full_name ?? null,
    buyerPhone: summary?.customer_phone ?? null,
    buyerAddress: null,
    companyName: summary?.company_name ?? null,
    paymentStatusLabel: summary?.payment_status_label ?? null,
    estimatedTotal: tracking.estimated_total ?? summary?.estimated_total ?? null,
    products,
  });
}
