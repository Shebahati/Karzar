import { describe, expect, it } from "vitest";
import {
  CONTENT_IMAGE_QUALITY,
  CWV_BUDGETS,
  isPlpLcpIndex,
  lazyImageProps,
  LCP_IMAGE_QUALITY,
  lcpImageProps,
  meetsClsBudget,
  meetsInpBudget,
  meetsLcpBudget,
  PLP_LCP_CARD_COUNT,
} from "@/lib/cwv";

describe("CWV budgets", () => {
  it("uses Google good thresholds", () => {
    expect(CWV_BUDGETS.lcpMs).toBe(2500);
    expect(CWV_BUDGETS.cls).toBe(0.1);
    expect(CWV_BUDGETS.inpMs).toBe(200);
  });

  it("gates lab/field samples", () => {
    expect(meetsLcpBudget(2400)).toBe(true);
    expect(meetsLcpBudget(2501)).toBe(false);
    expect(meetsClsBudget(0.1)).toBe(true);
    expect(meetsClsBudget(0.11)).toBe(false);
    expect(meetsInpBudget(200)).toBe(true);
    expect(meetsInpBudget(201)).toBe(false);
  });
});

describe("image props", () => {
  it("marks LCP candidates high-priority at budget quality", () => {
    expect(lcpImageProps()).toEqual({
      priority: true,
      fetchPriority: "high",
      quality: LCP_IMAGE_QUALITY,
    });
    expect(LCP_IMAGE_QUALITY).toBe(75);
  });

  it("keeps non-LCP images lazy", () => {
    expect(lazyImageProps()).toEqual({
      loading: "lazy",
      quality: CONTENT_IMAGE_QUALITY,
    });
  });

  it("prioritizes first PLP row", () => {
    expect(PLP_LCP_CARD_COUNT).toBe(4);
    expect(isPlpLcpIndex(0)).toBe(true);
    expect(isPlpLcpIndex(3)).toBe(true);
    expect(isPlpLcpIndex(4)).toBe(false);
  });
});
