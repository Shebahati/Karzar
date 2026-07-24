import { describe, expect, it } from "vitest";
import {
  encodeCountryList,
  encodeIdList,
  parseCountryList,
  parseIdList,
  DEFAULT_MAX_PRICE,
  DEFAULT_MIN_PRICE,
} from "@/components/catalog/use-catalog-params";

describe("catalog URL list helpers", () => {
  it("parses and encodes brand id lists", () => {
    expect(parseIdList(null)).toEqual([]);
    expect(parseIdList("")).toEqual([]);
    expect(parseIdList("3")).toEqual([3]);
    expect(parseIdList("1,2,1,3")).toEqual([1, 2, 3]);
    expect(parseIdList("0,-1,abc")).toEqual([]);
    expect(encodeIdList([1, 2])).toBe("1,2");
    expect(encodeIdList([])).toBeNull();
  });

  it("parses and encodes country lists", () => {
    expect(parseCountryList(null)).toEqual([]);
    expect(parseCountryList("ژاپن")).toEqual(["ژاپن"]);
    expect(parseCountryList("آلمان, ژاپن,آلمان")).toEqual(["آلمان", "ژاپن"]);
    expect(encodeCountryList(["آلمان", "ژاپن"])).toBe("آلمان,ژاپن");
    expect(encodeCountryList([])).toBeNull();
  });

  it("exposes price defaults ۰ تا ۲۰۰ میلیون", () => {
    expect(DEFAULT_MIN_PRICE).toBe(0);
    expect(DEFAULT_MAX_PRICE).toBe(200_000_000);
  });
});
