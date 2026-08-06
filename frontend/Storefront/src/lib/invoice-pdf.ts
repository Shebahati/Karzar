import type { OrderTracking } from "@/types/order";
import { formatToman, toPersianDigits } from "@/lib/utils";
import { ORDER_STATUS_LABELS } from "@/lib/constants";
import {
  STORE_ADDRESS_FA,
  STORE_EMAIL,
  STORE_NAME_FA,
  STORE_PHONE_DISPLAY,
} from "@/lib/store-location";

const BRAND_RED = "#D02327";
const BRAND_STEEL = "#5E5F5E";

/** Cart line shape for sample proforma — UI login-gated; no order required. */
export interface CartProformaLineInput {
  productId: number;
  name: string;
  sku: string;
  quantity: number;
  unitPrice: string | null;
}

/** Buyer identity for sample cart proforma (from account `full_name`). */
export interface CartProformaBuyer {
  fullName: string;
  phone?: string | null;
}

/** Catalog enrichment for order line labels (not inventing API fields). */
export interface InvoiceProductHint {
  name?: string;
  sku?: string;
}

export type InvoiceDocKind = "invoice" | "proforma" | "sample";

export interface DownloadOrderPdfOptions {
  kind?: "invoice" | "proforma";
  buyerName?: string | null;
  buyerPhone?: string | null;
  buyerAddress?: string | null;
  companyName?: string | null;
  paymentStatusLabel?: string | null;
  estimatedTotal?: string | null;
  /** product_id → name/sku from catalog when tracking omits them */
  products?: Record<number, InvoiceProductHint> | Map<number, InvoiceProductHint>;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function fa(value: string | number | null | undefined): string {
  return toPersianDigits(value ?? "");
}

function moneyFa(value: string | number | null | undefined): string {
  return formatToman(value);
}

function displayOrBlank(value: string | null | undefined): string {
  const t = (value ?? "").trim();
  return t || "—";
}

function lineTotalNum(qty: number, unit: string | null | undefined): number | null {
  if (unit == null || unit === "") return null;
  const n = Number(unit) * qty;
  return Number.isNaN(n) ? null : n;
}

/** Persian (Jalali) calendar date with Persian digits. */
function formatPersianDate(date: Date): string {
  return new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

function formatPersianDateShort(isoOrDate: string | Date): string {
  const date = typeof isoOrDate === "string" ? new Date(isoOrDate) : isoOrDate;
  if (Number.isNaN(date.getTime())) return fa(String(isoOrDate).slice(0, 10));
  return new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function absoluteAssetUrl(path: string): string {
  if (typeof window === "undefined") return path;
  return new URL(path, window.location.origin).href;
}

function absoluteFontUrl(file: string): string {
  return absoluteAssetUrl(`/fonts/${file}`);
}

/** Header wordmark — image only; no «کارزار» / «Karzar» text in letterhead. */
const BRAND_LOGO_PATH = "/images/brand/logo.svg";

function productHint(
  products: DownloadOrderPdfOptions["products"],
  productId: number,
): InvoiceProductHint | undefined {
  if (!products) return undefined;
  if (products instanceof Map) return products.get(productId);
  return products[productId];
}

interface InvoiceDocModel {
  kind: InvoiceDocKind;
  title: string;
  badge?: string;
  refLabel: string;
  refCode: string;
  dateLabel: string;
  buyerName: string;
  buyerPhone: string;
  buyerAddress: string;
  companyName?: string;
  statusLabel?: string;
  modeLabel?: string;
  paymentNote?: string;
  lines: Array<{
    sku: string;
    name: string;
    qty: number;
    unitPrice: string | null;
    lineTotal: number | null;
  }>;
  subtotal: number | null;
  taxLabel: string;
  grandLabel: string;
  estimatedTotal: number | null;
  footerNote: string;
  fileHint: string;
}

function buildDocumentHtml(model: InvoiceDocModel): string {
  const regular = absoluteFontUrl("IRANYekanX-Regular.woff2");
  const medium = absoluteFontUrl("IRANYekanX-Medium.woff2");
  const bold = absoluteFontUrl("IRANYekanX-Bold.woff2");
  const logoUrl = absoluteAssetUrl(BRAND_LOGO_PATH);

  /* Visual system is shared for invoice / proforma / sample —
   * kind only drives title, labels, badge, and legal footer copy. */
  const isSample = model.kind === "sample";
  const accent = BRAND_STEEL;
  const grandBg = "#f5f5f5";
  const grandFg = "#111";

  const rows =
    model.lines.length === 0
      ? `<tr><td colspan="6" class="empty">آیتمی ثبت نشده است</td></tr>`
      : model.lines
          .map((line, i) => {
            const sku = escapeHtml(fa(line.sku || "—"));
            const name = escapeHtml(line.name || "—");
            const qty = escapeHtml(fa(line.qty));
            const unit = escapeHtml(moneyFa(line.unitPrice));
            const total =
              line.lineTotal == null
                ? "—"
                : escapeHtml(moneyFa(line.lineTotal));
            return `<tr>
              <td class="c row-num">${escapeHtml(fa(i + 1))}</td>
              <td class="sku tnum">${sku}</td>
              <td class="name">${name}</td>
              <td class="c tnum">${qty}</td>
              <td class="num tnum">${unit}</td>
              <td class="num tnum">${total}</td>
            </tr>`;
          })
          .join("");

  const badge = model.badge
    ? `<span class="badge">${escapeHtml(model.badge)}</span>`
    : "";

  const companyRow =
    model.companyName && model.companyName.trim()
      ? `<p><span class="label">شرکت</span><span class="value">${escapeHtml(model.companyName)}</span></p>`
      : "";

  const metaExtra = [
    model.statusLabel
      ? `<div class="meta-cell"><span class="meta-k">وضعیت سفارش</span><strong class="meta-v">${escapeHtml(model.statusLabel)}</strong></div>`
      : "",
    model.modeLabel
      ? `<div class="meta-cell"><span class="meta-k">نوع سند</span><strong class="meta-v">${escapeHtml(model.modeLabel)}</strong></div>`
      : "",
  ].join("");

  const paymentBanner = model.paymentNote
    ? `<div class="pay-note" role="note"><span>وضعیت پرداخت / یادداشت</span><strong>${escapeHtml(model.paymentNote)}</strong></div>`
    : "";

  const totalsBlock = `
    <div class="totals-wrap">
      <div class="totals">
        <div class="total-row"><span>جمع جزء</span><strong class="tnum">${
          model.subtotal == null || model.subtotal <= 0
            ? "—"
            : escapeHtml(moneyFa(model.subtotal))
        }</strong></div>
        <div class="total-row muted"><span>مالیات / عوارض</span><strong>${escapeHtml(model.taxLabel)}</strong></div>
        <div class="total-row grand"><span>${escapeHtml(model.grandLabel)}</span><strong class="tnum">${
          model.estimatedTotal == null || model.estimatedTotal <= 0
            ? "—"
            : escapeHtml(moneyFa(model.estimatedTotal))
        }</strong></div>
      </div>
    </div>`;

  return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(model.fileHint)}</title>
  <style>
    @font-face {
      font-family: "IRANYekanX";
      src: url("${regular}") format("woff2");
      font-weight: 400;
      font-style: normal;
      font-display: block;
    }
    @font-face {
      font-family: "IRANYekanX";
      src: url("${medium}") format("woff2");
      font-weight: 500;
      font-style: normal;
      font-display: block;
    }
    @font-face {
      font-family: "IRANYekanX";
      src: url("${bold}") format("woff2");
      font-weight: 700;
      font-style: normal;
      font-display: block;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      background: #ececec;
      color: #1a1a1a;
      font-family: "IRANYekanX", Tahoma, Arial, sans-serif;
      font-size: 12px;
      line-height: 1.75;
      direction: rtl;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .toolbar {
      position: sticky;
      top: 0;
      z-index: 2;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
      align-items: center;
      padding: 12px 14px;
      background: rgba(255,255,255,.97);
      border-bottom: 1px solid #e2e2e2;
      font-family: "IRANYekanX", Tahoma, sans-serif;
    }
    .toolbar button {
      appearance: none;
      border: 0;
      border-radius: 6px;
      padding: 9px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    .toolbar .print {
      background: ${BRAND_RED};
      color: #fff;
    }
    .toolbar .close {
      background: #efefef;
      color: ${BRAND_STEEL};
    }
    .toolbar .hint {
      color: ${BRAND_STEEL};
      font-size: 11px;
      max-width: 28rem;
      text-align: center;
    }
    .sheet {
      position: relative;
      width: 210mm;
      min-height: 297mm;
      margin: 18px auto;
      background: #fff;
      padding: 0 0 18mm;
      box-shadow: 0 12px 40px rgba(0,0,0,.1);
      overflow: hidden;
    }
    .sheet::before {
      content: "";
      display: block;
      height: 5px;
      background: linear-gradient(90deg, ${BRAND_RED} 0%, ${BRAND_RED} 62%, ${BRAND_STEEL} 62%, ${BRAND_STEEL} 100%);
    }
    .sheet-inner {
      padding: 12mm 14mm 0;
    }
    .letterhead {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      gap: 14px;
      padding-bottom: 18px;
      border-bottom: 1px solid #e8e8e8;
    }
    .brand-logo {
      display: block;
      width: auto;
      height: 42px;
      max-width: 240px;
      object-fit: contain;
    }
    .doc-title {
      color: #111;
      font-size: 22px;
      font-weight: 700;
      line-height: 1.3;
      letter-spacing: -0.01em;
    }
    .doc-title-rule {
      width: 48px;
      height: 3px;
      margin: -4px auto 0;
      background: ${accent};
      border-radius: 2px;
    }
    .badge {
      display: inline-block;
      margin-top: 2px;
      padding: 3px 11px;
      border: 1px solid ${isSample ? BRAND_RED : "#d0d0d0"};
      border-radius: 3px;
      background: ${isSample ? "#fdf2f2" : "#f6f6f6"};
      color: ${isSample ? BRAND_RED : BRAND_STEEL};
      font-size: 10.5px;
      font-weight: 700;
    }
    .toolbar .fallback {
      flex: 1 1 100%;
      color: ${BRAND_RED};
      font-size: 11.5px;
      font-weight: 700;
      text-align: center;
      display: none;
    }
    .toolbar.needs-fallback .fallback { display: block; }
    .meta {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0;
      margin: 18px 0 0;
      border: 1px solid #e6e6e6;
      border-radius: 4px;
      overflow: hidden;
    }
    .meta-cell {
      display: flex;
      flex-direction: column;
      gap: 3px;
      padding: 11px 14px;
      border-bottom: 1px solid #ececec;
      border-left: 1px solid #ececec;
      background: #fafafa;
    }
    .meta-cell:nth-child(2n) { border-left: 0; }
    .meta-cell:nth-last-child(-n+2) { border-bottom: 0; }
    .meta-k {
      color: ${BRAND_STEEL};
      font-size: 10px;
      font-weight: 500;
    }
    .meta-v {
      color: #151515;
      font-size: 12.5px;
      font-weight: 700;
    }
    .parties {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin: 18px 0 20px;
    }
    .party {
      border: 1px solid #e4e4e4;
      border-radius: 4px;
      padding: 0;
      overflow: hidden;
      background: #fff;
    }
    .party h3 {
      margin: 0;
      padding: 8px 14px;
      background: ${BRAND_STEEL};
      color: #fff;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.02em;
    }
    .party.seller h3 { background: ${BRAND_RED}; }
    .party-body { padding: 12px 14px 14px; }
    .party p {
      color: #222;
      font-size: 11.5px;
      margin: 5px 0;
      display: flex;
      gap: 8px;
      align-items: baseline;
    }
    .party .label {
      color: ${BRAND_STEEL};
      flex: 0 0 3.4rem;
      font-size: 10.5px;
      font-weight: 500;
    }
    .party .value { flex: 1; min-width: 0; }
    table.items {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      border: 1px solid #ddd;
      border-radius: 4px;
      overflow: hidden;
    }
    table.items thead th {
      background: ${accent};
      color: #fff;
      font-weight: 700;
      font-size: 10.5px;
      padding: 10px 8px;
      text-align: center;
      letter-spacing: 0.01em;
    }
    table.items thead th:nth-child(3) { text-align: right; }
    table.items tbody td {
      border-bottom: 1px solid #ececec;
      padding: 10px 8px;
      vertical-align: top;
      font-size: 11px;
      color: #1f1f1f;
    }
    table.items tbody tr:last-child td { border-bottom: 0; }
    table.items tbody tr:nth-child(even) td { background: #f9f9f9; }
    td.c { text-align: center; width: 7%; }
    td.row-num { color: ${BRAND_STEEL}; font-weight: 500; }
    td.sku { text-align: center; width: 15%; word-break: break-all; color: ${BRAND_STEEL}; }
    td.name { text-align: right; width: 38%; font-weight: 500; }
    td.num { text-align: left; width: 17%; white-space: nowrap; }
    td.empty {
      text-align: center;
      color: ${BRAND_STEEL};
      padding: 22px 8px;
      background: #fafafa;
    }
    .tnum { font-variant-numeric: tabular-nums; }
    .totals-wrap {
      display: flex;
      justify-content: flex-start;
      margin-top: 16px;
    }
    .totals {
      width: min(300px, 100%);
      border: 1px solid #e0e0e0;
      border-radius: 4px;
      overflow: hidden;
      background: #fff;
    }
    .total-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      padding: 9px 14px;
      border-bottom: 1px solid #eee;
      font-size: 11.5px;
    }
    .total-row:last-child { border-bottom: 0; }
    .total-row.muted { color: ${BRAND_STEEL}; background: #fafafa; }
    .total-row.grand {
      background: ${grandBg};
      color: ${grandFg};
      font-size: 13.5px;
      font-weight: 700;
      padding: 12px 14px;
      border-top: 2px solid ${accent};
    }
    .pay-note {
      margin-top: 16px;
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 10px 14px;
      border: 1px dashed #d8d8d8;
      border-radius: 4px;
      background: #fcfcfc;
      font-size: 11.5px;
    }
    .pay-note span { color: ${BRAND_STEEL}; }
    .pay-note strong { color: #151515; font-weight: 700; }
    .footer {
      margin-top: 28px;
      padding-top: 14px;
      border-top: 1px solid #e4e4e4;
    }
    .footer p {
      color: ${BRAND_STEEL};
      font-size: 10.5px;
      line-height: 1.85;
    }
    .footer .brand {
      margin-top: 12px;
      color: ${BRAND_RED};
      font-weight: 700;
      font-size: 12px;
    }
    .footer .contact {
      margin-top: 4px;
      font-size: 10px;
      color: #888;
    }
    @page { size: A4; margin: 8mm; }
    @media print {
      html, body { background: #fff !important; }
      .toolbar { display: none !important; }
      .sheet {
        margin: 0;
        padding: 0;
        box-shadow: none;
        width: auto;
        min-height: 0;
      }
      .sheet-inner { padding: 2mm 4mm 0; }
    }
  </style>
</head>
<body>
  <div class="toolbar" id="toolbar">
    <button type="button" class="print" id="btn-print">چاپ / ذخیره PDF</button>
    <button type="button" class="close" id="btn-close">بستن</button>
    <span class="hint">برای دریافت PDF، در پنجره چاپ گزینه «ذخیره به‌صورت PDF» را انتخاب کنید.</span>
    <p class="fallback" id="print-fallback" role="alert">
      اگر پنجره چاپ باز نشد، روی «چاپ / ذخیره PDF» بزنید یا Ctrl+P (⌘P) را فشار دهید.
      در صورت مسدود بودن پاپ‌آپ، اجازه را در مرورگر فعال کنید و دوباره از سایت اقدام کنید.
    </p>
  </div>
  <article class="sheet" dir="rtl" lang="fa">
    <div class="sheet-inner">
      <header class="letterhead">
        <img
          class="brand-logo"
          src="${escapeHtml(logoUrl)}"
          alt=""
          width="240"
          height="38"
        />
        <h1 class="doc-title">${escapeHtml(model.title)}</h1>
        <div class="doc-title-rule" aria-hidden="true"></div>
        ${badge}
      </header>

      <section class="meta" aria-label="اطلاعات سند">
        <div class="meta-cell">
          <span class="meta-k">${escapeHtml(model.refLabel)}</span>
          <strong class="meta-v tnum">${escapeHtml(fa(model.refCode))}</strong>
        </div>
        <div class="meta-cell">
          <span class="meta-k">تاریخ</span>
          <strong class="meta-v tnum">${escapeHtml(model.dateLabel)}</strong>
        </div>
        ${metaExtra}
      </section>

      <section class="parties">
        <div class="party seller">
          <h3>فروشنده</h3>
          <div class="party-body">
            <p><span class="label">نام</span><span class="value">${escapeHtml(STORE_NAME_FA)}</span></p>
            <p><span class="label">آدرس</span><span class="value">${escapeHtml(STORE_ADDRESS_FA)}</span></p>
            <p><span class="label">تلفن</span><span class="value tnum">${escapeHtml(fa(STORE_PHONE_DISPLAY))}</span></p>
            <p><span class="label">ایمیل</span><span class="value">${escapeHtml(STORE_EMAIL)}</span></p>
          </div>
        </div>
        <div class="party">
          <h3>خریدار</h3>
          <div class="party-body">
            <p><span class="label">نام مشتری</span><span class="value">${escapeHtml(model.buyerName)}</span></p>
            ${companyRow}
            <p><span class="label">تلفن</span><span class="value tnum">${escapeHtml(model.buyerPhone)}</span></p>
            <p><span class="label">آدرس</span><span class="value">${escapeHtml(model.buyerAddress)}</span></p>
          </div>
        </div>
      </section>

      <table class="items">
        <thead>
          <tr>
            <th>ردیف</th>
            <th>کد / SKU</th>
            <th>شرح کالا</th>
            <th>تعداد</th>
            <th>فی (تومان)</th>
            <th>مبلغ ردیف</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>

      ${totalsBlock}
      ${paymentBanner}

      <footer class="footer">
        <p>${escapeHtml(model.footerNote)}</p>
        <p class="brand">${escapeHtml(STORE_NAME_FA)}</p>
        <p class="contact tnum">${escapeHtml(fa(STORE_PHONE_DISPLAY))} · ${escapeHtml(STORE_EMAIL)}</p>
      </footer>
    </div>
  </article>
</body>
</html>`;
}

function waitWithTimeout(promise: Promise<unknown>, ms: number): Promise<void> {
  return Promise.race([
    promise.then(() => undefined),
    new Promise<void>((resolve) => setTimeout(resolve, ms)),
  ]);
}

async function waitForPrintAssets(win: Window): Promise<void> {
  try {
    const fonts = win.document.fonts;
    if (fonts?.ready) {
      await waitWithTimeout(fonts.ready, 2500);
    }
  } catch {
    /* Tahoma fallback still readable */
  }

  const logo = win.document.querySelector<HTMLImageElement>("img.brand-logo");
  if (logo && !logo.complete) {
    await waitWithTimeout(
      new Promise<void>((resolve) => {
        logo.addEventListener("load", () => resolve(), { once: true });
        logo.addEventListener("error", () => resolve(), { once: true });
      }),
      2000,
    );
  }
}

function bindPrintToolbar(win: Window): void {
  const printBtn = win.document.getElementById("btn-print");
  const closeBtn = win.document.getElementById("btn-close");
  const toolbar = win.document.getElementById("toolbar");

  const triggerPrint = () => {
    try {
      win.focus();
      win.print();
    } catch {
      toolbar?.classList.add("needs-fallback");
    }
  };

  printBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    triggerPrint();
  });
  closeBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    win.close();
  });

  // Expose for opener-driven auto-print after fonts load.
  (win as Window & { __karzarPrint?: () => void }).__karzarPrint = triggerPrint;
}

/**
 * Open a print-ready HTML document (UTF-8 + IRANYekanX) so Persian glyphs
 * render correctly. Browser "Save as PDF" produces the downloadable file.
 * Avoids jsPDF default fonts which cannot encode Farsi (mojibake).
 *
 * Print is driven from the opener (not inline script/onclick) because the
 * storefront CSP (nonce + strict-dynamic) can inherit into about:blank popups
 * and block inline handlers — which made «چاپ / ذخیره PDF» appear dead.
 */
async function openPrintableDocument(model: InvoiceDocModel): Promise<void> {
  if (typeof window === "undefined") {
    throw new Error("PRINT_UNAVAILABLE");
  }

  const html = buildDocumentHtml(model);
  const win = window.open("", "_blank");
  if (!win) {
    throw new Error("POPUP_BLOCKED");
  }

  win.document.open();
  win.document.write(html);
  win.document.close();

  try {
    bindPrintToolbar(win);
    await waitForPrintAssets(win);
  } catch {
    /* window may have been closed during asset wait */
  }

  if (win.closed) return;

  // Let layout settle after @font-face / logo paint, then auto-open print.
  await new Promise((resolve) => setTimeout(resolve, 350));

  if (win.closed) return;

  try {
    win.focus();
    const printFn = (win as Window & { __karzarPrint?: () => void }).__karzarPrint;
    if (printFn) printFn();
    else win.print();
  } catch {
    try {
      win.document.getElementById("toolbar")?.classList.add("needs-fallback");
    } catch {
      /* ignore */
    }
  }
}

/**
 * Generate a branded printable document for a purchase invoice or inquiry proforma.
 * Uses HTML + IRANYekanX (not jsPDF) so Persian text renders without mojibake.
 */
export async function downloadOrderPdf(
  tracking: OrderTracking,
  kindOrOptions:
    | "invoice"
    | "proforma"
    | DownloadOrderPdfOptions = tracking.mode === "inquiry" ? "proforma" : "invoice",
): Promise<void> {
  const options: DownloadOrderPdfOptions =
    typeof kindOrOptions === "string" ? { kind: kindOrOptions } : kindOrOptions;

  const kind: "invoice" | "proforma" =
    options.kind ??
    (tracking.mode === "inquiry" ? "proforma" : "invoice");

  const items = tracking.items ?? [];
  let subtotal: number | null = 0;
  let hasPriced = false;

  const lines = items.map((item) => {
    const hint = productHint(options.products, item.product_id);
    const lt = lineTotalNum(item.quantity, item.unit_price);
    if (lt != null) {
      hasPriced = true;
      subtotal = (subtotal ?? 0) + lt;
    }
    return {
      sku: hint?.sku?.trim() || String(item.product_id),
      name:
        hint?.name?.trim() ||
        `کالای شماره ${fa(item.product_id)}`,
      qty: item.quantity,
      unitPrice: item.unit_price,
      lineTotal: lt,
    };
  });

  if (!hasPriced) subtotal = null;

  const totalSource =
    options.estimatedTotal ?? tracking.estimated_total ?? null;
  const estimated =
    totalSource != null && totalSource !== ""
      ? Number(totalSource)
      : subtotal;

  const paymentNote = displayOrBlank(options.paymentStatusLabel);
  const hasPaymentNote =
    options.paymentStatusLabel != null &&
    options.paymentStatusLabel.trim() !== "";

  await openPrintableDocument({
    kind,
    title: kind === "proforma" ? "پیش‌فاکتور" : "فاکتور خرید",
    badge: kind === "proforma" ? "استعلام" : undefined,
    refLabel: kind === "invoice" ? "شماره فاکتور" : "شماره مرجع",
    refCode: tracking.tracking_code,
    dateLabel: formatPersianDateShort(tracking.created_at),
    buyerName: displayOrBlank(options.buyerName),
    buyerPhone: displayOrBlank(
      options.buyerPhone ? fa(options.buyerPhone) : options.buyerPhone,
    ),
    buyerAddress: displayOrBlank(options.buyerAddress),
    companyName: options.companyName?.trim()
      ? options.companyName.trim()
      : undefined,
    statusLabel:
      tracking.status_label ||
      ORDER_STATUS_LABELS[tracking.status] ||
      tracking.status,
    modeLabel: tracking.mode === "inquiry" ? "استعلام" : "خرید",
    paymentNote: hasPaymentNote ? paymentNote : undefined,
    lines,
    subtotal,
    taxLabel: "—",
    grandLabel: kind === "invoice" ? "مبلغ کل" : "مبلغ تقریبی کل",
    estimatedTotal:
      estimated != null && !Number.isNaN(estimated) ? estimated : null,
    footerNote:
      kind === "proforma"
        ? "این پیش‌فاکتور جنبه اطلاع‌رسانی دارد و فاکتور مالیاتی رسمی محسوب نمی‌شود."
        : "از خرید شما سپاسگزاریم. این فاکتور خرید بر اساس اقلام ثبت‌شده سفارش صادر شده است. کارزار — فروشگاه ابزار صنعتی.",
    fileHint:
      kind === "proforma"
        ? `پیش‌فاکتور ${tracking.tracking_code}`
        : `فاکتور خرید ${tracking.tracking_code}`,
  });
}

/**
 * Client-side cart proforma from current lines (storefront login gate required).
 * No payment and no order creation — labelled sample until a live quote API exists.
 *
 * Opens a print-ready HTML page with IRANYekanX so Persian encodes correctly.
 * Live API only exposes admin `POST /orders/{id}/quote` after an inquiry order
 * exists — until a public preview ships, this labelled «پیش‌فاکتور نمونه» is local.
 */
export async function downloadCartSampleProforma(
  lines: CartProformaLineInput[],
  buyer: CartProformaBuyer,
): Promise<void> {
  if (lines.length === 0) {
    throw new Error("EMPTY_CART");
  }

  const buyerName = buyer.fullName.trim();
  if (!buyerName) {
    throw new Error("MISSING_BUYER_NAME");
  }

  const stamp = new Date();
  const sampleCode = `نمونه-${stamp.getTime().toString(36).toUpperCase()}`;

  let subtotal = 0;
  let hasPriced = false;

  const mapped = lines.map((line) => {
    const lt = lineTotalNum(line.quantity, line.unitPrice);
    if (lt != null) {
      hasPriced = true;
      subtotal += lt;
    }
    return {
      sku: line.sku || String(line.productId),
      name: line.name,
      qty: line.quantity,
      unitPrice: line.unitPrice,
      lineTotal: lt,
    };
  });

  await openPrintableDocument({
    kind: "sample",
    title: "پیش‌فاکتور",
    badge: "نمونه",
    refLabel: "شماره مرجع",
    refCode: sampleCode,
    dateLabel: formatPersianDate(stamp),
    buyerName,
    buyerPhone: displayOrBlank(buyer.phone),
    buyerAddress: "—",
    modeLabel: "پیش‌نمایش نمونه",
    lines: mapped,
    subtotal: hasPriced ? subtotal : null,
    taxLabel: "محاسبه نشده",
    grandLabel: "مبلغ تقریبی کل",
    estimatedTotal: hasPriced ? subtotal : null,
    footerNote:
      "این پیش‌فاکتور نمونه فقط برای پیش‌نمایش اقلام سبد خرید است؛ سند رسمی، مالیاتی یا تعهدآور نیست و بدون پرداخت صادر شده است. قیمت‌ها تقریبی‌اند و ممکن است پس از استعلام نهایی تغییر کنند.",
    fileHint: `پیش‌فاکتور نمونه ${fa(stamp.toISOString().slice(0, 10))}`,
  });
}
