import { describe, expect, it } from "vitest";
import { sanitizeNextPath } from "@/lib/sanitize-next-path";
import { stepUpPinSchema } from "@/lib/validation";

describe("sanitizeNextPath", () => {
  it("returns / for null or empty", () => {
    expect(sanitizeNextPath(null)).toBe("/");
    expect(sanitizeNextPath("")).toBe("/");
  });

  it("allows relative same-origin paths", () => {
    expect(sanitizeNextPath("/catalog/products")).toBe("/catalog/products");
    expect(sanitizeNextPath("/orders?x=1")).toBe("/orders?x=1");
  });

  it("blocks protocol-relative and absolute URLs", () => {
    expect(sanitizeNextPath("//evil.com")).toBe("/");
    expect(sanitizeNextPath("https://evil.com")).toBe("/");
    expect(sanitizeNextPath("javascript:alert(1)")).toBe("/");
  });
});

describe("stepUpPinSchema", () => {
  it("accepts a valid PIN length", () => {
    expect(stepUpPinSchema.parse("84729101")).toBe("84729101");
  });

  it("rejects too-short PIN", () => {
    expect(() => stepUpPinSchema.parse("123")).toThrow();
  });
});
