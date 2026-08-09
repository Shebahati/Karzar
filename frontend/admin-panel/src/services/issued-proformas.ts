/**
 * Issued-proformas data layer.
 *
 * Current adapter: localStorage (browser-only, per-device).
 * Live multi-admin sync requires BE endpoints — see `IssuedProformasApiStub`
 * in `@/types/invoice-doc`. Flip by replacing the body of these methods;
 * callers (`features/invoices/*`) stay unchanged.
 *
 * Storage is intentionally scoped to this origin (admin panel). Storefront
 * cart-sample proformas on another port/origin cannot share this registry
 * without a shared API or same-site cookie bridge — deferred to BE.
 */

import type {
  IssuedProformaCreateInput,
  IssuedProformaRecord,
  InvoiceDocumentPayload,
  InvoiceLineInput,
} from "@/types/invoice-doc";

export const ISSUED_PROFORMAS_STORAGE_KEY = "karzar.admin.issued-proformas.v1";

/** Soft cap so a busy browser profile cannot grow forever. */
const MAX_RECORDS = 200;

function emptyBuyerTotals(lines: InvoiceLineInput[]): number {
  return lines.reduce((sum, line) => sum + lineNetToman(line), 0);
}

export function lineGrossToman(line: InvoiceLineInput): number {
  const qty = Math.max(0, Number(line.quantity) || 0);
  const unit = Math.max(0, Number(line.unitPriceToman) || 0);
  return Math.round(unit * qty);
}

/**
 * Line discount in toman. Prefer percent when set; otherwise flat amount.
 * Builder UI clears the other field so they stay alternatives (not stacked).
 */
export function lineDiscountToman(line: InvoiceLineInput): number {
  const gross = lineGrossToman(line);
  const pct = Math.min(100, Math.max(0, Number(line.discountPercent) || 0));
  if (pct > 0) {
    return Math.min(gross, Math.round((gross * pct) / 100));
  }
  const flat = Math.max(0, Number(line.discountAmountToman) || 0);
  return Math.min(gross, flat);
}

export function lineNetToman(line: InvoiceLineInput): number {
  return Math.max(0, lineGrossToman(line) - lineDiscountToman(line));
}

export function documentGrandTotalToman(doc: InvoiceDocumentPayload): number {
  return emptyBuyerTotals(doc.lines);
}

function readStore(): IssuedProformaRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(ISSUED_PROFORMAS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isRecordShape);
  } catch {
    return [];
  }
}

function writeStore(rows: IssuedProformaRecord[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ISSUED_PROFORMAS_STORAGE_KEY, JSON.stringify(rows));
}

function isRecordShape(value: unknown): value is IssuedProformaRecord {
  if (!value || typeof value !== "object") return false;
  const r = value as IssuedProformaRecord;
  return (
    typeof r.id === "string" &&
    typeof r.refCode === "string" &&
    typeof r.createdAt === "string" &&
    r.document != null &&
    typeof r.document === "object"
  );
}

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `pf-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

const DEMO_SEED_FLAG = "karzar.admin.issued-proformas.demo-seeded.v1";

function makeDemoRecords(): IssuedProformaRecord[] {
  const now = Date.now();
  const demos: IssuedProformaCreateInput[] = [
    {
      source: "invoice-builder",
      document: {
        kind: "proforma",
        refCode: "PF-DEMO-1001",
        createdAt: new Date(now - 1000 * 60 * 60 * 26).toISOString(),
        buyer: {
          fullName: "علی رضایی",
          companyName: "کارگاه رضایی",
          phone: "02188776655",
          mobile: "09121234567",
          address: "تهران، خیابان انقلاب",
          postalCode: "1136985631",
          nationalId: "",
        },
        lines: [
          {
            productId: 1,
            name: "دریل چکشی صنعتی",
            sku: "DRL-100",
            quantity: 2,
            unitPriceToman: 1_850_000,
            discountPercent: 10,
            discountAmountToman: 0,
          },
          {
            productId: 2,
            name: "صفحه برش فلز",
            sku: "CUT-220",
            quantity: 5,
            unitPriceToman: 320_000,
            discountPercent: 0,
            discountAmountToman: 100_000,
          },
        ],
      },
    },
    {
      source: "invoice-builder",
      document: {
        kind: "proforma",
        refCode: "PF-DEMO-1002",
        createdAt: new Date(now - 1000 * 60 * 60 * 5).toISOString(),
        buyer: {
          fullName: "مریم حسینی",
          companyName: "",
          phone: "",
          mobile: "09351234567",
          address: "",
          postalCode: "",
          nationalId: "",
        },
        lines: [
          {
            productId: 3,
            name: "آچار بکس مجموعه",
            sku: "WCH-050",
            quantity: 1,
            unitPriceToman: 4_200_000,
            discountPercent: 0,
            discountAmountToman: 0,
          },
        ],
      },
    },
  ];
  return demos.map((input) => toRecord(input));
}

/** One-time demo rows so the issued list isn’t empty on first local open. */
function ensureDemoSeed(): void {
  if (typeof window === "undefined") return;
  const existing = readStore();
  const seeded = window.localStorage.getItem(DEMO_SEED_FLAG) === "1";
  if (existing.length > 0) {
    if (!seeded) window.localStorage.setItem(DEMO_SEED_FLAG, "1");
    return;
  }
  if (seeded) return;
  writeStore(makeDemoRecords());
  window.localStorage.setItem(DEMO_SEED_FLAG, "1");
}

function toRecord(
  input: IssuedProformaCreateInput,
): IssuedProformaRecord {
  const doc = input.document;
  const buyerName =
    doc.buyer.companyName.trim() ||
    doc.buyer.fullName.trim() ||
    "—";
  return {
    id: newId(),
    kind: doc.kind,
    refCode: doc.refCode,
    createdAt: doc.createdAt,
    buyerName,
    buyerPhone: doc.buyer.mobile.trim() || doc.buyer.phone.trim() || "",
    buyerAddress: doc.buyer.address.trim() || "",
    lineCount: doc.lines.length,
    grandTotalToman: documentGrandTotalToman(doc),
    document: doc,
    source: input.source ?? "invoice-builder",
  };
}

export const issuedProformasService = {
  /**
   * List newest-first.
   * Seeds 1–2 demo rows once when the store is empty (local UX only).
   * BE later: GET /admin/proformas
   */
  async list(): Promise<IssuedProformaRecord[]> {
    ensureDemoSeed();
    const rows = readStore();
    return [...rows].sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );
  },

  /**
   * BE later: GET /admin/proformas/:id
   */
  async get(id: string): Promise<IssuedProformaRecord | null> {
    return readStore().find((r) => r.id === id) ?? null;
  },

  /**
   * Persist a generated document (typically kind=proforma).
   * Does **not** write to backend DB.
   * BE later: POST /admin/proformas
   */
  async create(input: IssuedProformaCreateInput): Promise<IssuedProformaRecord> {
    const record = toRecord(input);
    const next = [record, ...readStore()].slice(0, MAX_RECORDS);
    writeStore(next);
    return record;
  },

  /**
   * BE later: DELETE /admin/proformas/:id
   */
  async remove(id: string): Promise<void> {
    writeStore(readStore().filter((r) => r.id !== id));
  },

  /** Clear local registry (dev / troubleshooting). */
  async clearAll(): Promise<void> {
    writeStore([]);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(DEMO_SEED_FLAG);
    }
  },
};

/** Generate a local ref code for builder docs (not a tax invoice number). */
export function makeLocalRefCode(kind: "invoice" | "proforma"): string {
  const stamp = Date.now().toString(36).toUpperCase();
  const prefix = kind === "proforma" ? "PF" : "INV";
  return `${prefix}-${stamp}`;
}
