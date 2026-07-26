import { describe, expect, it } from "vitest";

import {
  isPaddingLeafName,
  prepareMegamenuNode,
  resolveMegamenuBold,
} from "@/lib/megamenu-display";

describe("megamenu-display", () => {
  it("detects عمومی padding leaf names", () => {
    expect(isPaddingLeafName("عمومی")).toBe(true);
    expect(isPaddingLeafName("کولیس — عمومی")).toBe(true);
    expect(isPaddingLeafName("انواع کولیس")).toBe(false);
  });

  it("collapses sole عمومی child into parent leaf", () => {
    const prepared = prepareMegamenuNode({
      id: 1,
      name: "کولیس",
      product_count: 10,
      subcategories: [{ id: 2, name: "کولیس — عمومی", product_count: 10, subcategories: [] }],
    });
    expect(prepared?.subcategories).toEqual([]);
  });

  it("honors megamenu_as_leaf and megamenu_hidden", () => {
    expect(
      prepareMegamenuNode({
        id: 1,
        name: "پنهان",
        megamenu_hidden: true,
        product_count: 5,
        subcategories: [],
      }),
    ).toBeNull();

    const forced = prepareMegamenuNode({
      id: 2,
      name: "والد",
      megamenu_as_leaf: true,
      product_count: 5,
      subcategories: [{ id: 3, name: "فرزند", product_count: 5, subcategories: [] }],
    });
    expect(forced?.subcategories).toEqual([]);
  });

  it("resolves bold auto vs override", () => {
    expect(resolveMegamenuBold({ id: 1, name: "a", megamenu_bold: null }, { isBranch: true })).toBe(
      true,
    );
    expect(
      resolveMegamenuBold({ id: 1, name: "a", megamenu_bold: null }, { isBranch: false }),
    ).toBe(false);
    expect(resolveMegamenuBold({ id: 1, name: "a", megamenu_bold: true }, { isBranch: false })).toBe(
      true,
    );
    expect(resolveMegamenuBold({ id: 1, name: "a", megamenu_bold: false }, { isBranch: true })).toBe(
      false,
    );
  });
});
