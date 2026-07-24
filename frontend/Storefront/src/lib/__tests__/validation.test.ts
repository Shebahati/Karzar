import { describe, expect, it } from "vitest";
import {
  contactSchema,
  guestSchema,
  phoneSchema,
  shippingSchema,
} from "@/lib/validation";

describe("phoneSchema", () => {
  it("accepts a valid Iranian mobile", () => {
    expect(phoneSchema.parse("09123456789")).toBe("09123456789");
  });

  it("normalizes Persian digits", () => {
    expect(phoneSchema.parse("۰۹۱۲۳۴۵۶۷۸۹")).toBe("09123456789");
  });

  it("rejects short or non-09 numbers", () => {
    expect(() => phoneSchema.parse("09123")).toThrow();
    expect(() => phoneSchema.parse("08123456789")).toThrow();
  });
});

describe("guestSchema", () => {
  it("requires full_name and phone", () => {
    const parsed = guestSchema.parse({ full_name: "علی رضایی", phone: "09120000000" });
    expect(parsed.phone).toBe("09120000000");
  });

  it("rejects short names", () => {
    expect(() => guestSchema.parse({ full_name: "ا", phone: "09120000000" })).toThrow();
  });
});

describe("shippingSchema", () => {
  it("accepts a complete address with 10-digit postal code", () => {
    const parsed = shippingSchema.parse({
      full_name: "علی رضایی",
      phone: "09120000000",
      province: "تهران",
      city: "تهران",
      postal_code: "1234567890",
      address_line: "خیابان ولیعصر، پلاک ۱۲۳",
      note: "",
    });
    expect(parsed.postal_code).toBe("1234567890");
  });

  it("rejects bad postal codes", () => {
    expect(() =>
      shippingSchema.parse({
        full_name: "علی رضایی",
        phone: "09120000000",
        province: "تهران",
        city: "تهران",
        postal_code: "12345",
        address_line: "خیابان ولیعصر، پلاک ۱۲۳",
      }),
    ).toThrow();
  });
});

describe("contactSchema", () => {
  it("requires a message of at least 10 characters", () => {
    expect(() =>
      contactSchema.parse({
        full_name: "علی",
        phone: "09120000000",
        subject: "سوال",
        message: "کوتاه",
      }),
    ).toThrow();
  });
});
