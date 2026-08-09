/**
 * Shared invoice / proforma document shapes for the admin Invoice Builder
 * and issued-proformas registry.
 *
 * Amounts are stored in **toman** (catalog unit). PDF rendering converts to rial (×۱۰).
 *
 * Persistence today: browser localStorage via `issuedProformasService`.
 * When BE ships list/save endpoints, swap only the service implementation —
 * these types stay stable.
 */

export type InvoiceDocKind = "invoice" | "proforma";

/** One editable builder / registry line. */
export interface InvoiceLineInput {
  /** Catalog product id when picked from products API; null for free-text rows. */
  productId: number | null;
  name: string;
  sku: string;
  quantity: number;
  /** Charged unit price in toman (prefilled from catalog, editable). */
  unitPriceToman: number;
  /** Flat line discount in toman (optional; used when percent is 0). */
  discountAmountToman: number;
  /** Line discount percent 0–100 (optional; takes precedence over flat amount). */
  discountPercent: number;
}

export interface InvoiceBuyerInput {
  fullName: string;
  companyName: string;
  phone: string;
  mobile: string;
  address: string;
  /** Postal code — required on invoice PDFs; optional blank slot on proforma. */
  postalCode?: string;
  nationalId: string;
}

/** Full document payload used by PDF + registry. */
export interface InvoiceDocumentPayload {
  kind: InvoiceDocKind;
  /** Human-facing ref / شماره (e.g. PF-…). */
  refCode: string;
  /** ISO-8601 created timestamp. */
  createdAt: string;
  buyer: InvoiceBuyerInput;
  lines: InvoiceLineInput[];
  /** Optional free-form note shown only in admin UI (not on PDF unless noted). */
  adminNote?: string;
}

/** Registry row — locally issued proformas (and optional invoice snapshots). */
export interface IssuedProformaRecord {
  id: string;
  /** Always "proforma" for the issued list; invoices may be stored separately later. */
  kind: InvoiceDocKind;
  refCode: string;
  createdAt: string;
  buyerName: string;
  buyerPhone: string;
  buyerAddress: string;
  lineCount: number;
  /** Grand total in toman (net after discounts). */
  grandTotalToman: number;
  /** Full payload for re-download / in-panel expand. */
  document: InvoiceDocumentPayload;
  source: "invoice-builder" | "api";
}

export interface IssuedProformaCreateInput {
  document: InvoiceDocumentPayload;
  source?: IssuedProformaRecord["source"];
}

/**
 * Future BE contract (stub). When live, `issuedProformasService` should call:
 * - GET  /admin/proformas
 * - GET  /admin/proformas/:id
 * - POST /admin/proformas
 * - DELETE /admin/proformas/:id  (optional)
 */
export interface IssuedProformasApiStub {
  list(): Promise<IssuedProformaRecord[]>;
  get(id: string): Promise<IssuedProformaRecord | null>;
  create(input: IssuedProformaCreateInput): Promise<IssuedProformaRecord>;
  remove(id: string): Promise<void>;
}
