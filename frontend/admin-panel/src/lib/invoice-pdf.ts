/**
 * Admin invoice / proforma PDF — adapted from Storefront `invoice-pdf.ts`.
 * Same visual system (header, seller/buyer, table, totals).
 * Pure client-side HTML → browser print / Save as PDF. No backend writes.
 */

import { formatNumber, toPersianDigits } from "@/lib/utils";
import { rialAmountInWords } from "@/lib/persian-amount-words";
import {
  STORE_ADDRESS_FA,
  STORE_EMAIL,
  STORE_PHONE_DISPLAY,
  STORE_TELEGRAM_URL,
} from "@/lib/store-location";
import {
  documentGrandTotalToman,
  lineDiscountToman,
  lineGrossToman,
  lineNetToman,
} from "@/services/issued-proformas";
import type {
  InvoiceDocKind,
  InvoiceDocumentPayload,
} from "@/types/invoice-doc";

const BRAND_RED = "#D02327";
const BRAND_STEEL = "#5E5F5E";
const COMPANY_TRADE_FA = "ابزار کارزار";
const TOMAN_TO_RIAL = 10;
const LINE_UNIT_FA = "عدد";
const PROFORMA_VALIDITY_HOURS = 24;
const BRAND_LOGO_PATH = "/images/brand/logo.svg";

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
  buyerAddress: string;
  buyerPostalCode: string;
  buyerNationalId: string;
  paymentLines: string[];
  lines: InvoiceLineModel[];
  qtySum: number;
  amountSumRial: number | null;
  discountSumRial: number;
  grandTotalRial: number | null;
  amountInWords: string;
  footerNote: string;
  fileHint: string;
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

function slotOrEmpty(value: string | null | undefined): string {
  return (value ?? "").trim();
}

function tomanToRial(toman: number | null): number | null {
  if (toman == null || Number.isNaN(toman)) return null;
  return Math.round(toman * TOMAN_TO_RIAL);
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

function telegramHandlePlain(): string {
  if (!STORE_TELEGRAM_URL) return "";
  return STORE_TELEGRAM_URL.replace(/^https?:\/\/t\.me\//i, "").replace(/^@+/, "");
}

function buildPaymentDetailLines(kind: InvoiceDocKind): string[] {
  const lines: string[] = [];
  if (kind === "proforma") {
    lines.push(
      `مدت زمان اعتبار پیش‌فاکتور ${fa(PROFORMA_VALIDITY_HOURS)} ساعت می‌باشد.`,
    );
  }
  if (kind === "invoice") {
    lines.push("پرداخت از طریق درگاه رسمی بانکی کارزار انجام می‌شود.");
  }
  if (STORE_TELEGRAM_URL) {
    const handle = telegramHandlePlain();
    if (handle) {
      lines.push(
        `در صورت واریز یا ارسال رسید پرداخت، از طریق تلگرام ${handle} با پشتیبانی هماهنگ کنید.`,
      );
    }
  }
  lines.push(`پشتیبانی: ${fa(STORE_PHONE_DISPLAY)} · ${STORE_EMAIL}`);
  return lines;
}

function payloadToModel(doc: InvoiceDocumentPayload): InvoiceDocModel {
  let qtySum = 0;
  let amountSumRial = 0;
  let discountSumRial = 0;
  let hasPriced = false;

  const lines: InvoiceLineModel[] = doc.lines.map((line) => {
    const qty = Math.max(0, Number(line.quantity) || 0);
    qtySum += qty;
    const grossToman = lineGrossToman(line);
    const discountToman = lineDiscountToman(line);
    const netToman = lineNetToman(line);
    const unitToman = Math.max(0, Number(line.unitPriceToman) || 0);

    const unitPriceRial = tomanToRial(unitToman);
    const amountRial = tomanToRial(grossToman);
    const discountRial = tomanToRial(discountToman) ?? 0;
    const totalRial = tomanToRial(netToman);

    if (amountRial != null) {
      hasPriced = true;
      amountSumRial += amountRial;
    }
    discountSumRial += discountRial;

    return {
      name: line.name,
      sku: line.sku,
      qty,
      unitPriceRial,
      amountRial,
      discountRial,
      totalRial,
    };
  });

  const grandToman = documentGrandTotalToman(doc);
  const grandTotalRial = tomanToRial(grandToman);

  const company = doc.buyer.companyName?.trim();
  const buyerName = displayOrBlank(doc.buyer.fullName);
  const buyerLabel = company
    ? company
    : buyerName !== "—"
      ? buyerName
      : "—";

  const phoneFa = doc.buyer.phone?.trim()
    ? fa(doc.buyer.phone.trim())
    : "—";
  const mobileFa = doc.buyer.mobile?.trim()
    ? fa(doc.buyer.mobile.trim())
    : phoneFa;

  const nationalIdFa = doc.buyer.nationalId?.trim()
    ? fa(doc.buyer.nationalId.trim())
    : "";

  const buyerAddress = slotOrEmpty(doc.buyer.address);
  const buyerPostalRaw = slotOrEmpty(doc.buyer.postalCode);
  if (doc.kind === "invoice" && (!buyerAddress || !buyerPostalRaw)) {
    throw new Error("MISSING_BUYER_ADDRESS");
  }
  const buyerPostalCode = buyerPostalRaw ? fa(buyerPostalRaw) : "";

  return {
    kind: doc.kind,
    title: doc.kind === "proforma" ? "پیش‌فاکتور" : "فاکتور",
    refCode: doc.refCode,
    dateLabel: formatPersianDateShort(doc.createdAt),
    buyerLabel,
    buyerPhone: phoneFa,
    buyerMobile: mobileFa,
    buyerAddress,
    buyerPostalCode,
    buyerNationalId: nationalIdFa || "—",
    paymentLines: buildPaymentDetailLines(doc.kind),
    lines,
    qtySum,
    amountSumRial: hasPriced ? amountSumRial : null,
    discountSumRial,
    grandTotalRial,
    amountInWords:
      grandTotalRial != null ? rialAmountInWords(grandTotalRial) : "—",
    footerNote:
      doc.kind === "proforma"
        ? "این پیش‌فاکتور جنبه اطلاع‌رسانی دارد و فاکتور مالیاتی رسمی محسوب نمی‌شود."
        : "از خرید شما سپاسگزاریم. این فاکتور بر اساس اقلام ثبت‌شده صادر شده است.",
    fileHint:
      doc.kind === "proforma"
        ? `پیش‌فاکتور ${doc.refCode}`
        : `فاکتور ${doc.refCode}`,
  };
}

function renderDocHeader(
  model: InvoiceDocModel,
  opts: { compact?: boolean; showLogo?: boolean } = {},
): string {
  const compact = Boolean(opts.compact);
  const showLogo = opts.showLogo !== false && !compact;
  const logoUrl = absoluteAssetUrl(BRAND_LOGO_PATH);
  const logoCell = showLogo
    ? `<div class="doc-logo">
        <img class="brand-logo" src="${escapeHtml(logoUrl)}" alt="" width="200" height="36" />
      </div>`
    : `<div class="doc-logo" aria-hidden="true"></div>`;
  return `
    <header class="doc-header${compact ? " compact" : ""}${showLogo ? "" : " no-logo"}">
      <div class="doc-meta">
        <div><span class="k">شماره:</span> <strong class="tnum">${escapeHtml(fa(model.refCode))}</strong></div>
        <div><span class="k">تاریخ:</span> <strong class="tnum">${escapeHtml(model.dateLabel)}</strong></div>
      </div>
      <div class="doc-titles">
        <h1 class="doc-title">${escapeHtml(model.title)}</h1>
        <p class="doc-company">${escapeHtml(COMPANY_TRADE_FA)}</p>
      </div>
      ${logoCell}
    </header>`;
}

function documentStyles(): string {
  const regular = absoluteFontUrl("IRANYekanX-Regular.woff2");
  const medium = absoluteFontUrl("IRANYekanX-Medium.woff2");
  const bold = absoluteFontUrl("IRANYekanX-Bold.woff2");
  return `
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
      background: linear-gradient(180deg, #fff 0%, #fafafa 100%);
      padding: 0 0 14mm;
      box-shadow: 0 12px 40px rgba(0,0,0,.1);
      overflow: hidden;
    }
    .sheet.embed {
      margin: 0 auto;
      box-shadow: 0 4px 20px rgba(0,0,0,.06);
      min-height: 0;
    }
    .sheet::before {
      content: "";
      display: block;
      height: 4px;
      background: linear-gradient(90deg, ${BRAND_RED} 0%, ${BRAND_RED} 58%, ${BRAND_STEEL} 58%, ${BRAND_STEEL} 100%);
    }
    .sheet-inner { padding: 9mm 11mm 0; }
    .doc-header {
      display: grid;
      grid-template-columns: 1.15fr auto 1.15fr;
      align-items: center;
      gap: 10px;
      padding-bottom: 10px;
      margin-bottom: 10px;
      border-bottom: 1px solid #e8e8e8;
    }
    .doc-header.compact { padding-bottom: 8px; margin-bottom: 10px; }
    .doc-meta { text-align: right; font-size: 11px; line-height: 1.85; }
    .doc-meta .k { color: ${BRAND_STEEL}; font-weight: 500; }
    .doc-meta strong { color: #151515; font-weight: 700; }
    .doc-titles { text-align: center; }
    .doc-title {
      color: #111;
      font-size: 20px;
      font-weight: 700;
      line-height: 1.25;
    }
    .doc-company {
      margin-top: 2px;
      color: ${BRAND_STEEL};
      font-size: 12px;
      font-weight: 700;
    }
    .doc-logo { display: flex; justify-content: flex-end; }
    .brand-logo {
      display: block;
      width: auto;
      height: 34px;
      max-width: 180px;
      object-fit: contain;
    }
    .doc-header.compact .brand-logo { height: 28px; }
    .doc-header.compact .doc-title { font-size: 16px; }
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
    /* Column shares (old → new): row/qty ×0.2, unit ×0.5, amounts ×0.8; freed → شرح */
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
    .sum-notes p { font-size: 10.5px; margin: 2px 0; color: #222; }
    .sum-notes .k { color: ${BRAND_STEEL}; font-weight: 500; }
    .sum-notes .words { font-weight: 600; line-height: 1.35; }
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
    .pay-block ul { list-style: none; padding: 0; margin: 0; }
    .pay-block li {
      position: relative;
      padding: 3px 0;
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
      margin-top: 28px;
      padding: 0 8px;
    }
    .sign {
      text-align: center;
      padding-top: 8px;
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
      html, body { background: #fff !important; }
      .toolbar { display: none !important; }
      .sheet {
        margin: 0;
        padding: 0;
        box-shadow: none;
        width: auto;
        min-height: 0;
        background: #fff;
      }
      .sheet-inner { padding: 2mm 3mm 0; }
    }
  `;
}

function buildSheetBody(model: InvoiceDocModel): string {
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

  const paymentLinesHtml = model.paymentLines
    .map((line) => `<li>${escapeHtml(line)}</li>`)
    .join("");

  const nationalRow =
    model.buyerNationalId && model.buyerNationalId !== "—"
      ? `<div class="info-row full">
          <div class="info-cell">
            <span class="k">کد ملی:</span>
            <span class="v tnum">${escapeHtml(model.buyerNationalId)}</span>
          </div>
        </div>`
      : "";

  return `
    ${renderDocHeader(model, { showLogo: true })}

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
          <span class="v">—</span>
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
          <span class="v tnum">${escapeHtml(model.buyerPhone)}</span>
        </div>
        <div class="info-cell">
          <span class="k">موبایل:</span>
          <span class="v tnum">${escapeHtml(model.buyerMobile)}</span>
        </div>
      </div>
      ${nationalRow}
      <div class="info-row">
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

    ${renderDocHeader(model, { compact: true, showLogo: false })}

    <section class="pay-block" aria-label="شرایط پرداخت">
      <ul>${paymentLinesHtml}</ul>
    </section>

    <div class="signs">
      <div class="sign">امضاء خریدار</div>
      <div class="sign">امضاء فروشنده</div>
    </div>

    <footer class="footer">
      <p>${escapeHtml(model.footerNote)}</p>
    </footer>
  `;
}

function buildDocumentHtml(
  model: InvoiceDocModel,
  opts: { embed?: boolean; showToolbar?: boolean } = {},
): string {
  const embed = Boolean(opts.embed);
  const showToolbar = opts.showToolbar !== false && !embed;
  const toolbar = showToolbar
    ? `<div class="toolbar" id="toolbar">
        <button type="button" class="print" id="btn-print">چاپ / ذخیره PDF</button>
        <button type="button" class="close" id="btn-close">بستن</button>
        <span class="hint">برای دریافت PDF، در پنجره چاپ گزینه «ذخیره به‌صورت PDF» را انتخاب کنید.</span>
        <p class="fallback" id="print-fallback" role="alert">
          اگر پنجره چاپ باز نشد، روی «چاپ / ذخیره PDF» بزنید یا Ctrl+P (⌘P) را فشار دهید.
        </p>
      </div>`
    : "";

  return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(model.fileHint)}</title>
  <style>${documentStyles()}</style>
</head>
<body>
  ${toolbar}
  <article class="sheet${embed ? " embed" : ""}" dir="rtl" lang="fa">
    <div class="sheet-inner">
      ${buildSheetBody(model)}
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
    if (fonts?.ready) await waitWithTimeout(fonts.ready, 2500);
  } catch {
    /* Tahoma fallback */
  }
  const logos = win.document.querySelectorAll<HTMLImageElement>("img.brand-logo");
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

async function openPrintableDocument(model: InvoiceDocModel): Promise<void> {
  if (typeof window === "undefined") throw new Error("PRINT_UNAVAILABLE");
  const html = buildDocumentHtml(model);
  const win = window.open("", "_blank");
  if (!win) throw new Error("POPUP_BLOCKED");

  win.document.open();
  win.document.write(html);
  win.document.close();

  try {
    bindPrintToolbar(win);
    await waitForPrintAssets(win);
  } catch {
    /* closed during wait */
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

/** HTML suitable for in-panel iframe preview (no print toolbar). */
export function buildInvoicePreviewHtml(doc: InvoiceDocumentPayload): string {
  return buildDocumentHtml(payloadToModel(doc), {
    embed: true,
    showToolbar: false,
  });
}

/** Open print / Save-as-PDF for an admin-built document. */
export async function downloadAdminInvoicePdf(
  doc: InvoiceDocumentPayload,
): Promise<void> {
  if (!doc.lines.length) throw new Error("EMPTY_LINES");
  const buyerOk =
    doc.buyer.fullName.trim() || doc.buyer.companyName.trim();
  if (!buyerOk) throw new Error("MISSING_BUYER");
  await openPrintableDocument(payloadToModel(doc));
}
