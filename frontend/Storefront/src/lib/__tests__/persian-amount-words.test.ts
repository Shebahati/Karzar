import { describe, expect, it } from "vitest";
import {
  numberToPersianWords,
  rialAmountInWords,
} from "@/lib/persian-amount-words";

describe("numberToPersianWords", () => {
  it("handles zero and small values", () => {
    expect(numberToPersianWords(0)).toBe("صفر");
    expect(numberToPersianWords(7)).toBe("هفت");
    expect(numberToPersianWords(15)).toBe("پانزده");
    expect(numberToPersianWords(21)).toBe("بیست و یک");
  });

  it("handles hundreds and thousands", () => {
    expect(numberToPersianWords(100)).toBe("یکصد");
    expect(numberToPersianWords(1018)).toBe("یک هزار و هجده");
    expect(numberToPersianWords(1_200_000)).toBe("یک میلیون و دویست هزار");
  });

  it("rejects invalid input", () => {
    expect(numberToPersianWords(-1)).toBe("");
    expect(numberToPersianWords(Number.NaN)).toBe("");
  });
});

describe("rialAmountInWords", () => {
  it("appends ریال", () => {
    expect(rialAmountInWords(0)).toBe("صفر ریال");
    expect(rialAmountInWords(10)).toBe("ده ریال");
  });
});
