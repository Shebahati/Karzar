import { jsPDF } from "jspdf";
import type { OrderTracking } from "@/types/order";
import { formatNumber, toPersianDigits } from "@/lib/utils";
import { ORDER_STATUS_LABELS } from "@/lib/constants";

const BRAND_RED: [number, number, number] = [194, 32, 38];
const BRAND_STEEL: [number, number, number] = [94, 95, 94];

function fa(value: string | number | null | undefined): string {
  return toPersianDigits(value ?? "");
}

function money(value: string | number | null | undefined): string {
  if (value == null || value === "") return "—";
  return `${formatNumber(value)} Toman`;
}

function lineTotal(
  qty: number,
  unit: string | null | undefined,
): string {
  if (unit == null || unit === "") return "—";
  const n = Number(unit) * qty;
  if (Number.isNaN(n)) return "—";
  return money(n);
}

/**
 * Generate a branded PDF for a purchase invoice or inquiry proforma.
 * Layout is LTR for jspdf glyph support; labels mix Persian (UTF-8 via default
 * fonts where possible) with English keys for reliable embedding.
 */
export async function downloadOrderPdf(
  tracking: OrderTracking,
  kind: "invoice" | "proforma" = tracking.mode === "inquiry" ? "proforma" : "invoice",
): Promise<void> {
  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const pageW = doc.internal.pageSize.getWidth();
  let y = 18;

  // Brand bar
  doc.setFillColor(...BRAND_RED);
  doc.rect(0, 0, pageW, 12, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(14);
  doc.setFont("helvetica", "bold");
  doc.text("KARZAR", 14, 8);
  doc.setFontSize(9);
  doc.setFont("helvetica", "normal");
  doc.text("Industrial Tools Storefront", pageW - 14, 8, { align: "right" });

  y = 24;
  doc.setTextColor(...BRAND_RED);
  doc.setFontSize(16);
  doc.setFont("helvetica", "bold");
  const title =
    kind === "proforma"
      ? "Proforma / Pish-Faktor (استعلام)"
      : "Purchase Invoice / Faktor (فاکتور خرید)";
  doc.text(title, 14, y);

  y += 10;
  doc.setDrawColor(...BRAND_STEEL);
  doc.setLineWidth(0.3);
  doc.line(14, y, pageW - 14, y);

  y += 8;
  doc.setTextColor(...BRAND_STEEL);
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");

  const meta: [string, string][] = [
    ["Tracking / کد پیگیری", fa(tracking.tracking_code)],
    ["Status / وضعیت", tracking.status_label || ORDER_STATUS_LABELS[tracking.status] || tracking.status],
    ["Mode / نوع", tracking.mode === "inquiry" ? "Inquiry / استعلام" : "Purchase / خرید"],
    ["Date / تاریخ", fa(tracking.created_at.slice(0, 10))],
  ];
  if (tracking.estimated_total) {
    meta.push(["Estimated total / مبلغ تقریبی", money(tracking.estimated_total)]);
  }
  if (tracking.postal_tracking_code) {
    meta.push(["Postal tracking / رهگیری پستی", fa(tracking.postal_tracking_code)]);
  }

  for (const [label, value] of meta) {
    doc.setFont("helvetica", "bold");
    doc.setTextColor(...BRAND_STEEL);
    doc.text(label, 14, y);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(30, 30, 30);
    doc.text(String(value), pageW - 14, y, { align: "right" });
    y += 7;
  }

  y += 4;
  doc.setFillColor(245, 245, 245);
  doc.rect(14, y - 5, pageW - 28, 8, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(...BRAND_STEEL);
  doc.text("Product ID", 16, y);
  doc.text("Qty", 60, y);
  doc.text("Unit price", 90, y);
  doc.text("Line total", pageW - 16, y, { align: "right" });
  y += 8;

  const items = tracking.items ?? [];
  doc.setFont("helvetica", "normal");
  doc.setTextColor(30, 30, 30);
  doc.setFontSize(9);

  if (items.length === 0) {
    doc.text("No line items available / آیتمی ثبت نشده", 16, y);
    y += 8;
  } else {
    for (const item of items) {
      if (y > 270) {
        doc.addPage();
        y = 20;
      }
      doc.text(fa(item.product_id), 16, y);
      doc.text(fa(item.quantity), 60, y);
      doc.text(money(item.unit_price), 90, y);
      doc.text(lineTotal(item.quantity, item.unit_price), pageW - 16, y, {
        align: "right",
      });
      y += 7;
    }
  }

  y += 6;
  doc.setDrawColor(...BRAND_RED);
  doc.setLineWidth(0.6);
  doc.line(14, y, pageW - 14, y);
  y += 10;

  doc.setFontSize(8);
  doc.setTextColor(...BRAND_STEEL);
  doc.text(
    kind === "proforma"
      ? "This proforma is informational and not a tax invoice. / این پیش‌فاکتور جنبه اطلاع‌رسانی دارد."
      : "Thank you for shopping with Karzar. / از خرید شما سپاسگزاریم.",
    14,
    y,
    { maxWidth: pageW - 28 },
  );
  y += 10;
  doc.setTextColor(...BRAND_RED);
  doc.setFont("helvetica", "bold");
  doc.text("karzar.ir", 14, y);

  const suffix = kind === "proforma" ? "proforma" : "invoice";
  doc.save(`karzar-${suffix}-${tracking.tracking_code}.pdf`);
}
