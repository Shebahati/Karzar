import { describe, expect, it } from "vitest";

import {
  productDetailToFormValues,
  productFormDefaults,
  toProductCreatePayload,
} from "@/features/catalog/product-schema";
import type { ProductDetail } from "@/types/product";

describe("logistics unknown-state round-trip", () => {
  it("defaults remain unknown and serialize as null", () => {
    expect(productFormDefaults.shipping_class).toBe("unknown");
    expect(productFormDefaults.shipping_is_fragile).toBe("unknown");
    expect(productFormDefaults.shipping_is_liquid).toBe("unknown");
    const payload = toProductCreatePayload({
      ...productFormDefaults,
      sku: "T-1",
      name: "Test",
      category_id: "3",
      tax_percent: "9",
    });
    expect(payload.shipping_class).toBeNull();
    expect(payload.shipping_is_fragile).toBeNull();
    expect(payload.shipping_is_liquid).toBeNull();
  });

  it("null detail fields map to unknown without becoming false/parcel", () => {
    const detail = {
      sku: "T-2",
      name: "Test",
      short_description: null,
      description: null,
      meta_title: null,
      meta_description: null,
      category_id: 3,
      brand_id: null,
      base_price: null,
      original_price: null,
      is_available: true,
      stock_unit: "piece",
      weight_grams: null,
      package_length_cm: null,
      package_width_cm: null,
      package_height_cm: null,
      shipping_is_fragile: null,
      shipping_is_liquid: null,
      shipping_class: null,
      tax_percent: "9",
      warranty_text: null,
      pdf_catalog_url: null,
      is_original: true,
      is_active: true,
      hesabfa_category_override_code: null,
      specifications: {},
    } as unknown as ProductDetail;

    const form = productDetailToFormValues(detail);
    expect(form.shipping_class).toBe("unknown");
    expect(form.shipping_is_fragile).toBe("unknown");
    expect(form.shipping_is_liquid).toBe("unknown");

    const payload = toProductCreatePayload(form);
    expect(payload.shipping_class).toBeNull();
    expect(payload.shipping_is_fragile).toBeNull();
    expect(payload.shipping_is_liquid).toBeNull();
  });

  it("explicit false/parcel round-trips without collapsing to unknown", () => {
    const detail = {
      sku: "T-3",
      name: "Test",
      short_description: null,
      description: null,
      meta_title: null,
      meta_description: null,
      category_id: 3,
      brand_id: null,
      base_price: "1000",
      original_price: null,
      is_available: true,
      stock_unit: "piece",
      weight_grams: "100",
      package_length_cm: "10",
      package_width_cm: "8",
      package_height_cm: "4",
      shipping_is_fragile: false,
      shipping_is_liquid: false,
      shipping_class: "parcel",
      tax_percent: "9",
      warranty_text: null,
      pdf_catalog_url: null,
      is_original: true,
      is_active: true,
      hesabfa_category_override_code: null,
      specifications: {},
    } as unknown as ProductDetail;

    const form = productDetailToFormValues(detail);
    expect(form.shipping_class).toBe("parcel");
    expect(form.shipping_is_fragile).toBe("false");
    expect(form.shipping_is_liquid).toBe("false");
    const payload = toProductCreatePayload(form);
    expect(payload.shipping_class).toBe("parcel");
    expect(payload.shipping_is_fragile).toBe(false);
    expect(payload.shipping_is_liquid).toBe(false);
  });
});
