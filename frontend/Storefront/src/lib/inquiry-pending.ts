/**
 * Guest inquiry "semi-account" — persist incomplete quote basket keyed by phone
 * so it can be restored after OTP login (decision 3).
 */

import type { CartLine } from "@/store/cart-store";

const STORAGE_KEY = "karzar.inquiry.pending";

export interface PendingInquiry {
  phone: string;
  full_name: string;
  tracking_code: string;
  created_at: string;
  lines: Array<{ product_id: number; quantity: number }>;
}

interface PendingStore {
  byPhone: Record<string, PendingInquiry>;
}

function readStore(): PendingStore {
  if (typeof window === "undefined") return { byPhone: {} };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { byPhone: {} };
    const parsed = JSON.parse(raw) as PendingStore;
    return parsed?.byPhone ? parsed : { byPhone: {} };
  } catch {
    return { byPhone: {} };
  }
}

function writeStore(store: PendingStore): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

export function savePendingInquiry(
  phone: string,
  payload: Omit<PendingInquiry, "phone">,
): void {
  const normalized = phone.replace(/\D/g, "");
  const store = readStore();
  store.byPhone[normalized] = { ...payload, phone: normalized };
  writeStore(store);
}

export function getPendingInquiry(phone: string): PendingInquiry | null {
  const normalized = phone.replace(/\D/g, "");
  return readStore().byPhone[normalized] ?? null;
}

export function clearPendingInquiry(phone: string): void {
  const normalized = phone.replace(/\D/g, "");
  const store = readStore();
  delete store.byPhone[normalized];
  writeStore(store);
}

export function pendingInquiryToCartLines(
  pending: PendingInquiry,
  products: Array<{ id: number; sku: string; name: string; thumbnail: string | null; base_price: string | null }>,
): CartLine[] {
  const byId = new Map(products.map((p) => [p.id, p]));
  const lines: CartLine[] = [];
  for (const line of pending.lines) {
    const product = byId.get(line.product_id);
    if (!product) continue;
    lines.push({
      product: {
        id: product.id,
        sku: product.sku,
        name: product.name,
        thumbnail: product.thumbnail,
        base_price: product.base_price,
        stock_status: "موجود",
        availability: true,
        is_original: true,
        category: null,
        brand: null,
      },
      quantity: line.quantity,
    });
  }
  return lines;
}
