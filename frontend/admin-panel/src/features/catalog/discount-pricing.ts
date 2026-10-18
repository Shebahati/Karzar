/**
 * Form-only price calculator. The API stores sale price in base_price and the
 * undiscounted reference in original_price; it does NOT accept discount_percent.
 * Calculate in integer hundredths of a toman to avoid floating-point drift.
 */
const PRICE = /^(0|[1-9]\d*)(?:\.(\d{1,2}))?$/;
const PERCENT = /^(\d{1,2})(?:\.(\d{1,2}))?$/;

function priceToHundredths(input: string): bigint {
  const match = PRICE.exec(input.trim());
  if (!match || match[1].length > 13) {
    throw new Error("قیمت باید عدد معتبر با حداکثر دو رقم اعشار باشد.");
  }
  return BigInt(match[1]) * BigInt(100) + BigInt((match[2] ?? "").padEnd(2, "0"));
}

function hundredthsToPrice(value: bigint): string {
  const whole = value / BigInt(100);
  const fraction = (value % BigInt(100)).toString().padStart(2, "0");
  return `${whole}.${fraction}`;
}

export interface CalculatedDiscount {
  basePrice: string;
  originalPrice: string;
}

/**
 * Always anchor to the undiscounted original when a valid one exists.
 * An inconsistent non-null original must be corrected explicitly; never
 * silently compound a discount or promote corrupt original_price (e.g. 10).
 * This only prepares form values; it never persists any catalog mutation.
 */
export function calculateProductDiscount(
  basePrice: string,
  originalPrice: string,
  percent: string,
): CalculatedDiscount {
  const match = PERCENT.exec(percent.trim());
  if (!match) throw new Error("درصد تخفیف باید بین ۰٫۰۱ و ۹۹٫۹۹ باشد.");
  const basisPoints = BigInt(match[1]) * BigInt(100) +
    BigInt((match[2] ?? "").padEnd(2, "0"));
  if (basisPoints <= BigInt(0) || basisPoints >= BigInt(10000)) {
    throw new Error("درصد تخفیف باید بین ۰٫۰۱ و ۹۹٫۹۹ باشد.");
  }

  const current = basePrice.trim() ? priceToHundredths(basePrice) : null;
  const original = originalPrice.trim() ? priceToHundredths(originalPrice) : null;
  if (original !== null && (current === null || original <= current)) {
    throw new Error("قیمت قبل از تخفیف ناسازگار است؛ ابتدا قیمت‌های فعلی را بررسی و اصلاح کنید.");
  }
  const anchor = original ?? current;
  if (anchor === null || anchor <= BigInt(0)) {
    throw new Error("ابتدا قیمت معتبر و تأییدشده محصول را وارد کنید.");
  }

  // ROUND_HALF_UP at a hundredth of a toman.
  const payable = (anchor * (BigInt(10000) - basisPoints) + BigInt(5000)) / BigInt(10000);
  if (payable <= BigInt(0)) throw new Error("قیمت نهایی باید بزرگ‌تر از صفر باشد.");
  return { basePrice: hundredthsToPrice(payable), originalPrice: hundredthsToPrice(anchor) };
}
