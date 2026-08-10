import { describe, expect, it } from "vitest";

import {
  documentGrandTotalToman,
  lineDiscountToman,
  lineGrossToman,
  lineNetToman,
  makeLocalRefCode,
} from "@/services/issued-proformas";
import type { InvoiceDocumentPayload, InvoiceLineInput } from "@/types/invoice-doc";

function line(partial: Partial<InvoiceLineInput>): InvoiceLineInput {
  return {
    productId: null,
    name: "x",
    sku: "sku",
    quantity: 2,
    unitPriceToman: 1_000_000,
    discountAmountToman: 0,
    discountPercent: 0,
    ...partial,
  };
}

describe("issued-proformas line math", () => {
  it("computes gross and percent discount", () => {
    const row = line({ discountPercent: 10 });
    expect(lineGrossToman(row)).toBe(2_000_000);
    expect(lineDiscountToman(row)).toBe(200_000);
    expect(lineNetToman(row)).toBe(1_800_000);
  });

  it("uses flat amount when percent is zero", () => {
    const row = line({ discountAmountToman: 150_000 });
    expect(lineDiscountToman(row)).toBe(150_000);
    expect(lineNetToman(row)).toBe(1_850_000);
  });

  it("prefers percent over flat when both present", () => {
    const row = line({ discountPercent: 50, discountAmountToman: 1 });
    expect(lineDiscountToman(row)).toBe(1_000_000);
  });

  it("sums document grand total", () => {
    const doc: InvoiceDocumentPayload = {
      kind: "proforma",
      refCode: "PF-1",
      createdAt: new Date().toISOString(),
      buyer: {
        fullName: "علی",
        companyName: "",
        phone: "",
        mobile: "",
        address: "",
        postalCode: "",
        nationalId: "",
      },
      lines: [
        line({ quantity: 1, unitPriceToman: 100, discountPercent: 10 }),
        line({ quantity: 1, unitPriceToman: 50, discountAmountToman: 5 }),
      ],
    };
    expect(documentGrandTotalToman(doc)).toBe(90 + 45);
  });

  it("builds local ref codes", () => {
    expect(makeLocalRefCode("proforma")).toMatch(/^PF-/);
    expect(makeLocalRefCode("invoice")).toMatch(/^INV-/);
  });
});
