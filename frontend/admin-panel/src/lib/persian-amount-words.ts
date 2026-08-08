/**
 * Convert a non-negative integer to Persian words (for invoice amount lines).
 * Supports up to billions; returns empty string for non-finite / negative input.
 */

const ONES = [
  "",
  "یک",
  "دو",
  "سه",
  "چهار",
  "پنج",
  "شش",
  "هفت",
  "هشت",
  "نه",
];
const TEENS = [
  "ده",
  "یازده",
  "دوازده",
  "سیزده",
  "چهارده",
  "پانزده",
  "شانزده",
  "هفده",
  "هجده",
  "نوزده",
];
const TENS = [
  "",
  "",
  "بیست",
  "سی",
  "چهل",
  "پنجاه",
  "شصت",
  "هفتاد",
  "هشتاد",
  "نود",
];
const HUNDREDS = [
  "",
  "یکصد",
  "دویست",
  "سیصد",
  "چهارصد",
  "پانصد",
  "ششصد",
  "هفتصد",
  "هشتصد",
  "نهصد",
];

const SCALES = ["", "هزار", "میلیون", "میلیارد", "تریلیون"] as const;

function underThousand(n: number): string {
  if (n <= 0) return "";
  if (n < 10) return ONES[n];
  if (n < 20) return TEENS[n - 10];
  if (n < 100) {
    const t = Math.floor(n / 10);
    const o = n % 10;
    return o ? `${TENS[t]} و ${ONES[o]}` : TENS[t];
  }
  const h = Math.floor(n / 100);
  const rest = n % 100;
  const head = HUNDREDS[h];
  if (!rest) return head;
  return `${head} و ${underThousand(rest)}`;
}

/** Integer → Persian words (no currency suffix). */
export function numberToPersianWords(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "";
  const n = Math.floor(value);
  if (n === 0) return "صفر";

  const parts: string[] = [];
  let remaining = n;
  let scale = 0;

  while (remaining > 0 && scale < SCALES.length) {
    const chunk = remaining % 1000;
    if (chunk > 0) {
      const words = underThousand(chunk);
      const scaleWord = SCALES[scale];
      parts.unshift(scaleWord ? `${words} ${scaleWord}` : words);
    }
    remaining = Math.floor(remaining / 1000);
    scale += 1;
  }

  return parts.join(" و ");
}

/** Amount in Rials as «… ریال». */
export function rialAmountInWords(rial: number): string {
  const words = numberToPersianWords(rial);
  if (!words) return "—";
  return `${words} ریال`;
}
