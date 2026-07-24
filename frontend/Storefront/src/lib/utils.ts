import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge conditional class names while resolving Tailwind conflicts.
 * Last-writer-wins on conflicting utilities (e.g. `p-2` vs `p-4`).
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format an integer/decimal amount as Iranian Toman with Persian grouping. */
export function formatToman(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(numeric)) return "—";
  return `${new Intl.NumberFormat("fa-IR").format(numeric)} تومان`;
}

/** Localize a numeric value using Persian digits and grouping. */
export function formatNumber(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(numeric)) return "—";
  return new Intl.NumberFormat("fa-IR").format(numeric);
}

const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";

/** Convert Western/Arabic digits to Persian for display. */
export function toPersianDigits(input: string | number | null | undefined): string {
  if (input === null || input === undefined) return "";
  return String(input).replace(/\d/g, (d) => PERSIAN_DIGITS[Number(d)]);
}

/** Alias for display strings that may contain mixed Latin digits. */
export function faDigits(value: string | number | null | undefined): string {
  return toPersianDigits(value);
}

/** Convert Western/Persian digits in a string to plain Western digits. */
export function toEnglishDigits(input: string): string {
  const persian = "۰۱۲۳۴۵۶۷۸۹";
  const arabic = "٠١٢٣٤٥٦٧٨٩";
  return input.replace(/[۰-۹٠-٩]/g, (d) => {
    const p = persian.indexOf(d);
    if (p > -1) return String(p);
    return String(arabic.indexOf(d));
  });
}

/** Sleep helper used by the mock layer to simulate network latency. */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
