import { z } from "zod";
import { toEnglishDigits } from "@/lib/utils";

/** Iranian mobile number, tolerant of Persian/Arabic digits on input. */
export const phoneSchema = z
  .string()
  .min(1, "شماره موبایل الزامی است.")
  .transform((v) => toEnglishDigits(v).trim())
  .refine((v) => /^09\d{9}$/.test(v), "شماره موبایل معتبر نیست (مثال: 09123456789).");

export const guestSchema = z.object({
  full_name: z.string().min(2, "نام و نام خانوادگی را وارد کنید."),
  phone: phoneSchema,
});
export type GuestValues = z.input<typeof guestSchema>;

/** Shipping form for standard (priced) purchases. */
export const shippingSchema = z.object({
  full_name: z.string().min(2, "نام و نام خانوادگی را وارد کنید."),
  phone: phoneSchema,
  province: z.string().min(2, "استان را وارد کنید."),
  city: z.string().min(2, "شهر را وارد کنید."),
  postal_code: z
    .string()
    .transform((v) => toEnglishDigits(v).trim())
    .refine((v) => /^\d{10}$/.test(v), "کد پستی باید ۱۰ رقم باشد."),
  address_line: z.string().min(10, "نشانی کامل را وارد کنید."),
  note: z.string().max(500, "حداکثر ۵۰۰ کاراکتر.").optional().or(z.literal("")),
});
export type ShippingValues = z.input<typeof shippingSchema>;

/** Inquiry form for price-less (RFQ / pre-invoice) baskets. */
export const inquirySchema = z.object({
  full_name: z.string().min(2, "نام و نام خانوادگی را وارد کنید."),
  phone: phoneSchema,
  company_name: z.string().max(120).optional().or(z.literal("")),
  note: z.string().max(500, "حداکثر ۵۰۰ کاراکتر.").optional().or(z.literal("")),
});
export type InquiryValues = z.input<typeof inquirySchema>;

/** Contact Us form. */
export const contactSchema = z.object({
  full_name: z.string().min(2, "نام خود را وارد کنید."),
  phone: phoneSchema,
  subject: z.string().min(3, "موضوع را وارد کنید."),
  message: z.string().min(10, "متن پیام حداقل ۱۰ کاراکتر باشد."),
});
export type ContactValues = z.input<typeof contactSchema>;
