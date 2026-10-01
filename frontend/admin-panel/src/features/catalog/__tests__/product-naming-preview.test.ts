import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import type { ProductNamingPreview } from "@/types/product";

describe("product naming preview (Phase 2B)", () => {
  it("exposes read-only preview fields and manufacturer_code status", () => {
    const sample: ProductNamingPreview = {
      product_id: 1,
      preview_source: "persisted_canonical",
      current_name: "کولیس تست",
      proposed_name: null,
      state: "HOLD_MISSING_MANUFACTURER_CODE",
      confidence: "none",
      naming_standard_version: "karzar_product_naming_v1",
      profile: null,
      profile_resolution: "PROFILE_MISSING",
      warnings: [],
      reason_codes: ["missing_manufacturer_code"],
      used_fields: [],
      omitted_fields: [],
      governance: {
        product_type: false,
        manufacturer_code: false,
        brand_display: false,
        naming_profile: false,
        variant_facts: false,
      },
      product_type: null,
      brand: null,
      manufacturer_code: null,
      manufacturer_code_status: "unset",
      mutation_check: {
        before: { name: "کولیس تست" },
        after: { name: "کولیس تست" },
        unchanged: true,
      },
    };
    expect(sample.preview_source).toBe("persisted_canonical");
    expect(sample.manufacturer_code_status).toBe("unset");
    expect(sample.mutation_check?.unchanged).toBe(true);
  });

  it("preview section has no Apply/Rename mutation controls", () => {
    const src = readFileSync(
      resolve(
        __dirname,
        "../components/product-naming-preview-section.tsx",
      ),
      "utf8",
    );
    expect(src).toContain("نام استاندارد کارزار");
    expect(src).toContain("تأیید نشده / ثبت نشده");
    expect(src).toContain("پیش‌نمایش فقط‌خواندنی");
    expect(src).not.toContain("ذخیره نام پیشنهادی");
    expect(src).not.toContain("Approve and rename");
    expect(src).not.toMatch(/<\s*button[^>]*>[^<]*(Apply|Rename|اعمال)/i);
    expect(src).not.toMatch(/\bonClick=\{[^}]*rename/i);
  });

  it("catalog service only GETs naming-preview", () => {
    const src = readFileSync(
      resolve(__dirname, "../../../services/catalog.ts"),
      "utf8",
    );
    expect(src).toContain("getNamingPreview");
    expect(src).toMatch(/apiClient\.get<ProductNamingPreview>/);
    expect(src).toContain("/products/${productId}/naming-preview");
    expect(src).not.toMatch(/naming-preview\/candidate|naming-preview.*post/i);
  });
});
