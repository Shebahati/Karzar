import type { OrderTracking } from "@/types/order";
import { productLineSavings, productUnitSavings } from "@/types/product";
import { formatNumber, toPersianDigits } from "@/lib/utils";
import { rialAmountInWords } from "@/lib/persian-amount-words";
import {
  STORE_ADDRESS_FA,
  STORE_EMAIL,
  STORE_PHONE_DISPLAY,
  STORE_TELEGRAM_URL,
} from "@/lib/store-location";

const BRAND_RED = "#D02327";
const BRAND_STEEL = "#5E5F5E";
/** Trade name on formal docs (matches storefront SEO / letterhead). */
const COMPANY_TRADE_FA = "ابزار کارزار";
/** Seller postal code on formal invoice / proforma (fixed company value). */
const SELLER_POSTAL_CODE = "1137617888";
/** Catalog amounts are toman; formal invoices show rial (×۱۰). */
const TOMAN_TO_RIAL = 10;
const LINE_UNIT_FA = "عدد";
const PROFORMA_VALIDITY_HOURS = 24;

/** Cart line shape for cart proforma — UI login-gated; no order required. */
export interface CartProformaLineInput {
  productId: number;
  name: string;
  sku: string;
  quantity: number;
  /** Sale / charged unit price (toman). */
  unitPrice: string | null;
  /** Compare-at / list unit price before discount (toman). */
  originalPrice?: string | null;
  discountPercent?: number | null;
}

/** Buyer identity for cart proforma (from account + optional address book). */
export interface CartProformaBuyer {
  fullName: string;
  phone?: string | null;
  companyName?: string | null;
  /** Street / city line — optional on cart proforma (blank slot if missing). */
  address?: string | null;
  /** Postal code — optional on cart proforma (blank slot if missing). */
  postalCode?: string | null;
}

/** Catalog enrichment for order line labels (not inventing API fields). */
export interface InvoiceProductHint {
  name?: string;
  sku?: string;
  /** Compare-at unit price (toman) when catalog has a real discount. */
  originalPrice?: string | null;
  discountPercent?: number | null;
}

export type InvoiceDocKind = "invoice" | "proforma" | "sample";

export interface DownloadOrderPdfOptions {
  kind?: "invoice" | "proforma";
  buyerName?: string | null;
  buyerPhone?: string | null;
  buyerAddress?: string | null;
  buyerPostalCode?: string | null;
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

/** Numeric amount for table cells (Persian digits + grouping, no currency word). */
function moneyNumFa(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(numeric)) return "—";
  return formatNumber(numeric);
}

function displayOrBlank(value: string | null | undefined): string {
  const t = (value ?? "").trim();
  return t || "—";
}

/** Empty string when missing — used for optional proforma address / postal slots. */
function slotOrEmpty(value: string | null | undefined): string {
  return (value ?? "").trim();
}

function lineTotalNum(qty: number, unit: string | null | undefined): number | null {
  if (unit == null || unit === "") return null;
  const n = Number(unit) * qty;
  return Number.isNaN(n) ? null : n;
}

function tomanToRial(toman: number | null): number | null {
  if (toman == null || Number.isNaN(toman)) return null;
  return Math.round(toman * TOMAN_TO_RIAL);
}

/** Jalali date as YYYY/MM/DD with Persian digits (year left → day right). */
function formatPersianDateShort(isoOrDate: string | Date): string {
  const date = typeof isoOrDate === "string" ? new Date(isoOrDate) : isoOrDate;
  if (Number.isNaN(date.getTime())) return fa(String(isoOrDate).slice(0, 10));
  const parts = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const year = parts.find((p) => p.type === "year")?.value ?? "";
  const month = parts.find((p) => p.type === "month")?.value ?? "";
  const day = parts.find((p) => p.type === "day")?.value ?? "";
  return `${year}/${month}/${day}`;
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
/** Seller stamp / seal for signature block (public asset). */
const SELLER_STAMP_PATH = "/images/brand/seller-stamp.png";

function productHint(
  products: DownloadOrderPdfOptions["products"],
  productId: number,
): InvoiceProductHint | undefined {
  if (!products) return undefined;
  if (products instanceof Map) return products.get(productId);
  return products[productId];
}

function buildPaymentDetailLines(
  kind: InvoiceDocKind,
  paymentStatusLabel?: string | null,
): string[] {
  const lines: string[] = [];

  if (kind === "proforma" || kind === "sample") {
    lines.push(
      `مدت زمان اعتبار پیش‌فاکتور ${fa(PROFORMA_VALIDITY_HOURS)} ساعت می‌باشد.`,
    );
  }

  if (paymentStatusLabel && paymentStatusLabel.trim()) {
    lines.push(`وضعیت پرداخت: ${paymentStatusLabel.trim()}`);
  }

  if (kind === "invoice") {
    lines.push("پرداخت از طریق درگاه رسمی بانکی کارزار انجام می‌شود.");
  }

  // Public support channel already in store-location — strip leading @ from ID.
  if (STORE_TELEGRAM_URL) {
    const handle = STORE_TELEGRAM_URL.replace(/^https?:\/\/t\.me\//i, "").replace(
      /^@+/,
      "",
    );
    if (handle) {
      lines.push(
        `در صورت واریز یا ارسال رسید پرداخت، از طریق تلگرام ${handle} با پشتیبانی هماهنگ کنید.`,
      );
    }
  }

  lines.push(`پشتیبانی: ${fa(STORE_PHONE_DISPLAY)} · ${STORE_EMAIL}`);
  return lines;
}

interface InvoiceLineModel {
  name: string;
  sku: string;
  qty: number;
  unitPriceRial: number | null;
  amountRial: number | null;
  discountRial: number;
  totalRial: number | null;
}

interface InvoiceDocModel {
  kind: InvoiceDocKind;
  title: string;
  refCode: string;
  dateLabel: string;
  buyerLabel: string;
  buyerPhone: string;
  buyerMobile: string;
  /** Buyer street/city — may be blank on proforma/sample. */
  buyerAddress: string;
  /** Buyer postal code — may be blank on proforma/sample. */
  buyerPostalCode: string;
  paymentLines: string[];
  /** Account balances — only when real data exists (never invent). */
  previousBalanceRial: number | null;
  balanceWithInvoiceRial: number | null;
  lines: InvoiceLineModel[];
  qtySum: number;
  amountSumRial: number | null;
  discountSumRial: number;
  grandTotalRial: number | null;
  amountInWords: string;
  footerNote: string;
  fileHint: string;
}

function renderDocHeader(model: InvoiceDocModel): string {
  const logoUrl = absoluteAssetUrl(BRAND_LOGO_PATH);
  return `
    <header class="doc-header">
      <div class="doc-meta">
        <div><span class="k">شماره:</span> <strong class="tnum">${escapeHtml(fa(model.refCode))}</strong></div>
        <div><span class="k">تاریخ:</span> <strong class="tnum">${escapeHtml(model.dateLabel)}</strong></div>
      </div>
      <div class="doc-titles">
        <h1 class="doc-title">${escapeHtml(model.title)}</h1>
        <p class="doc-company">${escapeHtml(COMPANY_TRADE_FA)}</p>
      </div>
      <div class="doc-logo">
        <img
          class="brand-logo"
          src="${escapeHtml(logoUrl)}"
          alt=""
          width="200"
          height="36"
        />
      </div>
    </header>`;
}

function buildDocumentHtml(model: InvoiceDocModel): string {
  const regular = absoluteFontUrl("IRANYekanX-Regular.woff2");
  const medium = absoluteFontUrl("IRANYekanX-Medium.woff2");
  const bold = absoluteFontUrl("IRANYekanX-Bold.woff2");
  const sellerStampUrl = absoluteAssetUrl(SELLER_STAMP_PATH);

  const isSample = model.kind === "sample";

  const rows =
    model.lines.length === 0
      ? `<tr><td colspan="8" class="empty">آیتمی ثبت نشده است</td></tr>`
      : model.lines
          .map((line, i) => {
            const desc = line.sku
              ? `${escapeHtml(line.name)}<span class="sku-sub tnum">${escapeHtml(fa(line.sku))}</span>`
              : escapeHtml(line.name || "—");
            return `<tr>
              <td class="c row-num tnum">${escapeHtml(fa(i + 1))}</td>
              <td class="name">${desc}</td>
              <td class="c qty tnum">${escapeHtml(fa(line.qty))}</td>
              <td class="c unit">${escapeHtml(LINE_UNIT_FA)}</td>
              <td class="num tnum">${escapeHtml(moneyNumFa(line.unitPriceRial))}</td>
              <td class="num tnum">${escapeHtml(moneyNumFa(line.amountRial))}</td>
              <td class="num tnum">${escapeHtml(moneyNumFa(line.discountRial))}</td>
              <td class="num tnum strong">${escapeHtml(moneyNumFa(line.totalRial))}</td>
            </tr>`;
          })
          .join("");

  const balanceBlock =
    model.previousBalanceRial != null || model.balanceWithInvoiceRial != null
      ? `<div class="balance-lines">
          ${
            model.previousBalanceRial != null
              ? `<p><span class="k">مانده حساب از قبل:</span> <strong class="tnum">${escapeHtml(moneyNumFa(model.previousBalanceRial))}</strong> ریال</p>`
              : ""
          }
          ${
            model.balanceWithInvoiceRial != null
              ? `<p><span class="k">با احتساب فاکتور:</span> <strong class="tnum">${escapeHtml(moneyNumFa(model.balanceWithInvoiceRial))}</strong> ریال</p>`
              : ""
          }
        </div>`
      : "";

  const paymentLinesHtml = model.paymentLines
    .map((line) => `<li>${escapeHtml(line)}</li>`)
    .join("");

  const isProformaLike = model.kind === "proforma" || isSample;
  const disclaimerBanner = isProformaLike
    ? `<div class="sample-banner" role="note">تعهد آور نیست</div>`
    : "";

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
      background: #ffffff;
      color: #1a1a1a;
      font-family: "IRANYekanX", Tahoma, Arial, sans-serif;
      font-size: 11px;
      line-height: 1.65;
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
    .toolbar .print { background: ${BRAND_RED}; color: #fff; }
    .toolbar .close { background: #efefef; color: ${BRAND_STEEL}; }
    .toolbar .hint {
      color: ${BRAND_STEEL};
      font-size: 11px;
      max-width: 28rem;
      text-align: center;
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
    .sheet {
      position: relative;
      width: 210mm;
      min-height: 297mm;
      margin: 18px auto;
      background: #ffffff;
      padding: 0 0 14mm;
      box-shadow: 0 12px 40px rgba(0,0,0,.1);
      overflow: hidden;
    }
    .sheet::before {
      content: "";
      display: block;
      height: 4px;
      background: linear-gradient(90deg, ${BRAND_RED} 0%, ${BRAND_RED} 58%, ${BRAND_STEEL} 58%, ${BRAND_STEEL} 100%);
    }
    .sheet-inner { padding: 9mm 11mm 0; }
    .sample-banner {
      margin-top: 14px;
      padding: 7px 12px;
      border: 1px solid #f0c4c5;
      border-radius: 4px;
      background: #fdf5f5;
      color: ${BRAND_RED};
      font-size: 11px;
      font-weight: 700;
      text-align: center;
    }
    .doc-header {
      display: grid;
      grid-template-columns: 1.15fr auto 1.15fr;
      align-items: center;
      gap: 10px;
      padding-bottom: 10px;
      margin-bottom: 10px;
      border-bottom: 1px solid #e8e8e8;
    }
    .doc-meta {
      text-align: right;
      font-size: 11px;
      line-height: 1.85;
    }
    .doc-meta .k { color: ${BRAND_STEEL}; font-weight: 500; }
    .doc-meta strong { color: #151515; font-weight: 700; }
    .doc-titles { text-align: center; }
    .doc-title {
      color: #111;
      font-size: 20px;
      font-weight: 700;
      line-height: 1.25;
      letter-spacing: -0.01em;
    }
    .doc-company {
      margin-top: 2px;
      color: ${BRAND_STEEL};
      font-size: 12px;
      font-weight: 700;
    }
    /* Physical left: logo column is last in RTL grid */
    .doc-logo { display: flex; justify-content: flex-end; }
    .brand-logo {
      display: block;
      width: auto;
      height: 34px;
      max-width: 180px;
      object-fit: contain;
    }

    .info-box {
      border: 1px solid #cfcfcf;
      border-radius: 3px;
      margin-bottom: 8px;
      overflow: hidden;
      background: #fff;
    }
    .info-box.seller { border-color: #d8b0b1; }
    .info-row {
      display: grid;
      grid-template-columns: 1.4fr 1fr 1fr;
      gap: 0;
      border-bottom: 1px solid #e6e6e6;
    }
    .info-row:last-child { border-bottom: 0; }
    .info-row.full { grid-template-columns: 1fr; }
    .info-cell {
      padding: 7px 10px;
      font-size: 11px;
      border-left: 1px solid #e6e6e6;
    }
    .info-cell:last-child { border-left: 0; }
    .info-cell .k {
      color: ${BRAND_STEEL};
      font-weight: 500;
      margin-left: 4px;
    }
    .info-cell .v { color: #151515; font-weight: 600; }
    .info-row.full .info-cell { padding: 7px 10px; }

    table.items {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      border: 1px solid #cfcfcf;
      margin-top: 4px;
    }
    table.items thead th {
      background: #e8e8e8;
      color: #222;
      font-weight: 700;
      font-size: 9.5px;
      padding: 7px 4px;
      text-align: center;
      border: 1px solid #cfcfcf;
      line-height: 1.35;
    }
    table.items tbody td {
      border: 1px solid #d8d8d8;
      padding: 6px 4px;
      vertical-align: middle;
      font-size: 10px;
      color: #1f1f1f;
    }
    table.items tbody tr:nth-child(even) td { background: #fafafa; }
    td.c { text-align: center; }
    /* Row / qty / unit match amount cols; شرح takes the rest */
    col.col-row { width: 8%; }
    col.col-name { width: 44%; }
    col.col-qty { width: 8%; }
    col.col-unit { width: 8%; }
    col.col-amt { width: 8%; }
    td.row-num { width: 8%; color: ${BRAND_STEEL}; font-weight: 500; }
    td.name { text-align: right; width: 44%; font-weight: 500; padding-right: 6px; word-wrap: break-word; overflow-wrap: anywhere; }
    td.name .sku-sub {
      display: block;
      color: ${BRAND_STEEL};
      font-size: 9px;
      font-weight: 400;
      margin-top: 1px;
    }
    td.qty { width: 8%; }
    td.unit { width: 8%; }
    td.num { width: 8%; text-align: left; white-space: nowrap; direction: ltr; }
    td.strong { font-weight: 700; }
    td.empty {
      text-align: center;
      color: ${BRAND_STEEL};
      padding: 18px 8px;
      background: #fafafa;
    }
    .tnum { font-variant-numeric: tabular-nums; }

    .after-table {
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 10px;
      margin-top: 0;
      align-items: start;
    }
    .sum-notes {
      border: 1px solid #cfcfcf;
      border-top: 0;
      padding: 4px 10px;
      background: #fff;
      min-height: 36px;
    }
    .sum-notes p {
      font-size: 10.5px;
      margin: 2px 0;
      color: #222;
    }
    .sum-notes .k { color: ${BRAND_STEEL}; font-weight: 500; }
    .sum-notes .words { font-weight: 600; line-height: 1.35; }
    .balance-lines { margin-top: 6px; }
    .sum-table {
      border: 1px solid #cfcfcf;
      border-top: 0;
      width: 100%;
      border-collapse: collapse;
      background: #fff;
    }
    .sum-table td {
      border: 1px solid #d8d8d8;
      padding: 6px 8px;
      font-size: 10.5px;
    }
    .sum-table td.lab {
      background: #f3f3f3;
      color: ${BRAND_STEEL};
      font-weight: 600;
      text-align: center;
      width: 38%;
    }
    .sum-table td.val {
      text-align: left;
      direction: ltr;
      font-weight: 600;
    }
    .sum-table tr.grand td {
      background: #f7f7f7;
      font-weight: 700;
      font-size: 11.5px;
      border-top: 2px solid ${BRAND_RED};
    }
    .sum-table tr.grand td.lab { color: #111; background: #efefef; }

    .section-break {
      margin: 16px 0 14px;
      border: 0;
      border-top: 3px solid #222;
    }

    .pay-block {
      border: 1px solid #e0e0e0;
      border-radius: 4px;
      padding: 12px 14px;
      background: #fff;
    }
    .pay-block ul {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .pay-block li {
      position: relative;
      padding: 3px 0 3px 0;
      font-size: 11px;
      color: #222;
      line-height: 1.75;
    }
    .pay-block li::before {
      content: "";
      display: inline-block;
      width: 5px;
      height: 5px;
      margin-left: 8px;
      border-radius: 50%;
      background: ${BRAND_RED};
      vertical-align: middle;
    }

    .signs {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-top: 36px;
      padding: 0 8px;
    }
    .sign {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      color: ${BRAND_STEEL};
      font-size: 11px;
      font-weight: 600;
    }
    .sign-space {
      min-height: 176px;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 8px;
      background: #ffffff;
    }
    .seller-stamp {
      max-height: 176px;
      max-width: 280px;
      width: auto;
      height: auto;
      object-fit: contain;
      background: #ffffff;
    }
    .sign-label {
      color: ${BRAND_STEEL};
      font-size: 11px;
      font-weight: 600;
    }

    .footer {
      margin-top: 18px;
      padding-top: 10px;
      border-top: 1px solid #e4e4e4;
    }
    .footer p {
      color: ${BRAND_STEEL};
      font-size: 10px;
      line-height: 1.75;
    }

    @page { size: A4; margin: 7mm; }
    @media print {
      html, body { background: #ffffff !important; }
      .toolbar { display: none !important; }
      .sheet {
        margin: 0;
        padding: 0;
        box-shadow: none;
        width: auto;
        min-height: 0;
        background: #ffffff !important;
      }
      .sign-space,
      .seller-stamp { background: #ffffff !important; }
      .sheet-inner { padding: 2mm 3mm 0; }
      .section-break { break-before: avoid; }
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
      ${renderDocHeader(model)}

      <section class="info-box seller" aria-label="فروشنده">
        <div class="info-row">
          <div class="info-cell">
            <span class="k">فروشنده:</span>
            <span class="v">${escapeHtml(COMPANY_TRADE_FA)}</span>
          </div>
          <div class="info-cell">
            <span class="k">تلفن:</span>
            <span class="v tnum">${escapeHtml(fa(STORE_PHONE_DISPLAY))}</span>
          </div>
          <div class="info-cell">
            <span class="k">کدپستی:</span>
            <span class="v tnum">${escapeHtml(fa(SELLER_POSTAL_CODE))}</span>
          </div>
        </div>
        <div class="info-row full">
          <div class="info-cell">
            <span class="k">آدرس:</span>
            <span class="v">${escapeHtml(STORE_ADDRESS_FA)}</span>
          </div>
        </div>
      </section>

      <section class="info-box" aria-label="خریدار">
        <div class="info-row">
          <div class="info-cell">
            <span class="k">خریدار:</span>
            <span class="v">${escapeHtml(model.buyerLabel)}</span>
          </div>
          <div class="info-cell">
            <span class="k">تلفن:</span>
            <span class="v tnum">${escapeHtml(model.buyerMobile)}</span>
          </div>
          <div class="info-cell">
            <span class="k">کد پستی:</span>
            <span class="v tnum">${escapeHtml(model.buyerPostalCode)}</span>
          </div>
        </div>
        <div class="info-row full">
          <div class="info-cell">
            <span class="k">آدرس:</span>
            <span class="v">${escapeHtml(model.buyerAddress)}</span>
          </div>
        </div>
      </section>

      <table class="items">
        <colgroup>
          <col class="col-row" />
          <col class="col-name" />
          <col class="col-qty" />
          <col class="col-unit" />
          <col class="col-amt" />
          <col class="col-amt" />
          <col class="col-amt" />
          <col class="col-amt" />
        </colgroup>
        <thead>
          <tr>
            <th>ردیف</th>
            <th>شرح</th>
            <th>تعداد</th>
            <th>واحد</th>
            <th>مبلغ واحد<br/>(ریال)</th>
            <th>مبلغ<br/>(ریال)</th>
            <th>تخفیف<br/>(ریال)</th>
            <th>مبلغ کل<br/>(ریال)</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>

      <div class="after-table">
        <div class="sum-notes">
          <p class="words">
            <span class="k">مبلغ کل به حروف:</span>
            ${escapeHtml(model.amountInWords)}
          </p>
          ${balanceBlock}
        </div>
        <table class="sum-table" aria-label="جمع‌ها">
          <tr>
            <td class="lab">تعداد</td>
            <td class="val tnum">${escapeHtml(fa(model.qtySum))}</td>
          </tr>
          <tr>
            <td class="lab">مبلغ</td>
            <td class="val tnum">${escapeHtml(moneyNumFa(model.amountSumRial))}</td>
          </tr>
          <tr>
            <td class="lab">تخفیف</td>
            <td class="val tnum">${escapeHtml(moneyNumFa(model.discountSumRial))}</td>
          </tr>
          <tr class="grand">
            <td class="lab">مبلغ کل</td>
            <td class="val tnum">${escapeHtml(moneyNumFa(model.grandTotalRial))}</td>
          </tr>
        </table>
      </div>

      <hr class="section-break" />

      <section class="pay-block" aria-label="شرایط پرداخت">
        <ul>${paymentLinesHtml}</ul>
      </section>

      <div class="signs">
        <div class="sign">
          <div class="sign-space" aria-hidden="true"></div>
          <div class="sign-label">امضاء خریدار</div>
        </div>
        <div class="sign">
          <div class="sign-space">
            <img
              class="seller-stamp"
              src="${escapeHtml(sellerStampUrl)}"
              alt=""
            />
          </div>
          <div class="sign-label">مهر و امضای فروشنده</div>
        </div>
      </div>

      <footer class="footer">
        <p>${escapeHtml(model.footerNote)}</p>
      </footer>
      ${disclaimerBanner}
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

  const logos = win.document.querySelectorAll<HTMLImageElement>(
    "img.brand-logo, img.seller-stamp",
  );
  await Promise.all(
    [...logos].map((logo) => {
      if (logo.complete) return Promise.resolve();
      return waitWithTimeout(
        new Promise<void>((resolve) => {
          logo.addEventListener("load", () => resolve(), { once: true });
          logo.addEventListener("error", () => resolve(), { once: true });
        }),
        2000,
      );
    }),
  );
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

function mapPricedLines(
  raw: Array<{
    sku: string;
    name: string;
    qty: number;
    /** Sale / charged unit price (toman). */
    unitPrice: string | null;
    originalPrice?: string | null;
    discountPercent?: number | null;
    lineTotal: number | null;
  }>,
): {
  lines: InvoiceLineModel[];
  qtySum: number;
  amountSumRial: number | null;
  discountSumRial: number;
  hasPriced: boolean;
} {
  let qtySum = 0;
  let amountSumRial = 0;
  let discountSumRial = 0;
  let hasPriced = false;

  const lines = raw.map((line) => {
    qtySum += line.qty;
    const saleToman =
      line.unitPrice != null && line.unitPrice !== ""
        ? Number(line.unitPrice)
        : null;
    const saleOk = saleToman != null && !Number.isNaN(saleToman);

    const unitSavingsToman = saleOk
      ? productUnitSavings({
          base_price: line.unitPrice,
          original_price: line.originalPrice,
          discount_percent: line.discountPercent,
        })
      : 0;
    const discountToman = saleOk
      ? productLineSavings(
          {
            base_price: line.unitPrice,
            original_price: line.originalPrice,
            discount_percent: line.discountPercent,
          },
          line.qty,
        )
      : 0;

    // List/unit column: original when discounted, else sale.
    const listToman =
      saleOk && unitSavingsToman > 0 ? saleToman + unitSavingsToman : saleToman;

    const saleLineToman =
      line.lineTotal != null && !Number.isNaN(line.lineTotal)
        ? line.lineTotal
        : saleOk
          ? saleToman * line.qty
          : null;

    const amountToman =
      listToman != null && !Number.isNaN(listToman)
        ? listToman * line.qty
        : saleLineToman;

    const unitPriceRial = tomanToRial(listToman);
    const amountRial = tomanToRial(amountToman);
    const discountRial = tomanToRial(discountToman) ?? 0;
    const totalRial =
      saleLineToman != null
        ? tomanToRial(saleLineToman)
        : amountRial == null
          ? null
          : amountRial - discountRial;

    if (amountRial != null) {
      hasPriced = true;
      amountSumRial += amountRial;
    }
    discountSumRial += discountRial;

    return {
      name: line.name,
      sku: line.sku,
      qty: line.qty,
      unitPriceRial,
      amountRial,
      discountRial,
      totalRial,
    };
  });

  return {
    lines,
    qtySum,
    amountSumRial: hasPriced ? amountSumRial : null,
    discountSumRial,
    hasPriced,
  };
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
  let subtotalToman: number | null = 0;
  let hasPriced = false;

  const rawLines = items.map((item) => {
    const hint = productHint(options.products, item.product_id);
    const lt = lineTotalNum(item.quantity, item.unit_price);
    if (lt != null) {
      hasPriced = true;
      subtotalToman = (subtotalToman ?? 0) + lt;
    }
    return {
      sku: hint?.sku?.trim() || String(item.product_id),
      name:
        hint?.name?.trim() ||
        `کالای شماره ${fa(item.product_id)}`,
      qty: item.quantity,
      unitPrice: item.unit_price,
      originalPrice: hint?.originalPrice ?? null,
      discountPercent: hint?.discountPercent ?? null,
      lineTotal: lt,
    };
  });

  if (!hasPriced) subtotalToman = null;

  const totalSource =
    options.estimatedTotal ?? tracking.estimated_total ?? null;
  const estimatedToman =
    totalSource != null && totalSource !== ""
      ? Number(totalSource)
      : subtotalToman;

  const mapped = mapPricedLines(rawLines);
  const saleSumRial =
    mapped.hasPriced && mapped.amountSumRial != null
      ? mapped.amountSumRial - mapped.discountSumRial
      : null;
  const grandToman =
    estimatedToman != null && !Number.isNaN(estimatedToman)
      ? estimatedToman
      : saleSumRial != null
        ? saleSumRial / TOMAN_TO_RIAL
        : null;
  const resolvedGrandRial = tomanToRial(grandToman) ?? saleSumRial;

  const buyerName = displayOrBlank(options.buyerName);
  const company = options.companyName?.trim();
  const buyerLabel = company
    ? company
    : buyerName !== "—"
      ? buyerName
      : "—";
  const phoneFa = options.buyerPhone
    ? fa(options.buyerPhone)
    : "—";

  const buyerAddress = slotOrEmpty(options.buyerAddress);
  const buyerPostalRaw = slotOrEmpty(options.buyerPostalCode);
  if (kind === "invoice" && (!buyerAddress || !buyerPostalRaw)) {
    throw new Error("MISSING_BUYER_ADDRESS");
  }
  const buyerPostalCode = buyerPostalRaw ? fa(buyerPostalRaw) : "";

  await openPrintableDocument({
    kind,
    title: kind === "proforma" ? "پیش‌فاکتور" : "فاکتور",
    refCode: tracking.tracking_code,
    dateLabel: formatPersianDateShort(tracking.created_at),
    buyerLabel,
    buyerPhone: phoneFa,
    buyerMobile: phoneFa,
    buyerAddress,
    buyerPostalCode,
    paymentLines: buildPaymentDetailLines(kind, options.paymentStatusLabel),
    previousBalanceRial: null,
    balanceWithInvoiceRial: null,
    lines: mapped.lines,
    qtySum: mapped.qtySum,
    amountSumRial: mapped.amountSumRial,
    discountSumRial: mapped.discountSumRial,
    grandTotalRial: resolvedGrandRial,
    amountInWords:
      resolvedGrandRial != null
        ? rialAmountInWords(resolvedGrandRial)
        : "—",
    footerNote:
      kind === "proforma"
        ? "این پیش‌فاکتور جنبه اطلاع‌رسانی دارد و فاکتور مالیاتی رسمی محسوب نمی‌شود."
        : "از خرید شما سپاسگزاریم. این فاکتور بر اساس اقلام ثبت‌شده سفارش صادر شده است.",
    fileHint:
      kind === "proforma"
        ? `پیش‌فاکتور ${tracking.tracking_code}`
        : `فاکتور ${tracking.tracking_code}`,
  });
}

const CART_PROFORMA_SEQ_KEY = "karzar.storefront.cart-proforma-seq.v1";

/**
 * Next customer-facing cart proforma number (PF-00001…).
 * Sequential in this browser; never prefixed with «نمونه».
 */
function nextCartProformaRefCode(): string {
  let seq = 1;
  if (typeof window !== "undefined") {
    try {
      const raw = window.localStorage.getItem(CART_PROFORMA_SEQ_KEY);
      const parsed = raw ? Number.parseInt(raw, 10) : 0;
      if (Number.isFinite(parsed) && parsed >= 0) seq = parsed + 1;
      window.localStorage.setItem(CART_PROFORMA_SEQ_KEY, String(seq));
    } catch {
      seq = (Date.now() % 90000) + 10000;
    }
  }
  return `PF-${String(seq).padStart(5, "0")}`;
}

/**
 * Client-side cart proforma from current lines (storefront login gate required).
 * No payment and no order creation — local document with a real PF number until
 * a public cart-quote API exists.
 *
 * Opens a print-ready HTML page with IRANYekanX so Persian encodes correctly.
 * Live API only exposes admin `POST /orders/{id}/quote` after an inquiry order
 * exists — until a public preview ships, this is a local cart proforma document.
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
  const refCode = nextCartProformaRefCode();

  const rawLines = lines.map((line) => {
    const lt = lineTotalNum(line.quantity, line.unitPrice);
    return {
      sku: line.sku || String(line.productId),
      name: line.name,
      qty: line.quantity,
      unitPrice: line.unitPrice,
      originalPrice: line.originalPrice ?? null,
      discountPercent: line.discountPercent ?? null,
      lineTotal: lt,
    };
  });

  const mapped = mapPricedLines(rawLines);
  const grandTotalRial =
    mapped.amountSumRial != null
      ? mapped.amountSumRial - mapped.discountSumRial
      : null;
  const phoneFa = buyer.phone ? fa(buyer.phone) : "—";
  const company = buyer.companyName?.trim();
  const buyerLabel = company || buyerName;
  const buyerAddress = slotOrEmpty(buyer.address);
  const buyerPostalRaw = slotOrEmpty(buyer.postalCode);
  const buyerPostalCode = buyerPostalRaw ? fa(buyerPostalRaw) : "";

  await openPrintableDocument({
    kind: "proforma",
    title: "پیش‌فاکتور",
    refCode,
    dateLabel: formatPersianDateShort(stamp),
    buyerLabel,
    buyerPhone: phoneFa,
    buyerMobile: phoneFa,
    buyerAddress,
    buyerPostalCode,
    paymentLines: buildPaymentDetailLines("proforma", null),
    previousBalanceRial: null,
    balanceWithInvoiceRial: null,
    lines: mapped.lines,
    qtySum: mapped.qtySum,
    amountSumRial: mapped.amountSumRial,
    discountSumRial: mapped.discountSumRial,
    grandTotalRial,
    amountInWords:
      grandTotalRial != null
        ? rialAmountInWords(grandTotalRial)
        : "—",
    footerNote:
      "این پیش‌فاکتور جنبه اطلاع‌رسانی دارد و فاکتور مالیاتی رسمی محسوب نمی‌شود. قیمت‌ها ممکن است پس از استعلام نهایی تغییر کنند.",
    fileHint: `پیش‌فاکتور ${refCode}`,
  });
}
