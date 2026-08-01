"use client";

import { SafeImage } from "@/components/ui/safe-image";
import { formatToman, toPersianDigits } from "@/lib/utils";
import type { CartLine } from "@/store/cart-store";

export function OrderSummary({
  lines,
  isInquiry,
}: {
  lines: CartLine[];
  isInquiry: boolean;
}) {
  const total = lines.reduce(
    (sum, l) => sum + Number(l.product.base_price ?? 0) * l.quantity,
    0,
  );

  return (
    <div className="rounded-2xl bg-card p-6 shadow-card">
      <h2 className="text-base font-bold text-foreground">
        {isInquiry ? "اقلام استعلام" : "خلاصه سفارش"}
      </h2>

      <ul className="mt-4 space-y-3">
        {lines.map((line) => (
          <li key={line.product.id} className="flex items-center gap-3">
            <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-accent">
              <SafeImage
                src={line.product.thumbnail ?? ""}
                alt={line.product.name}
                fill
                sizes="56px"
                className="object-contain p-1"
                fallback={
                  <span className="grid h-full w-full place-items-center text-sm font-medium text-[#5E5F5E]">
                    {(line.product.name || "ک").slice(0, 1)}
                  </span>
                }
              />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <p className="line-clamp-2 text-sm font-bold leading-snug text-foreground">
                  {line.product.name}
                </p>
                <span
                  className="inline-flex shrink-0 items-center gap-0.5 rounded-md bg-[#D02327]/10 px-1.5 py-0.5 text-[11px] font-bold text-[#D02327] tnum"
                  aria-label={`تعداد ${toPersianDigits(line.quantity)}`}
                >
                  <span aria-hidden>×</span>
                  {toPersianDigits(line.quantity)}
                </span>
              </div>
              <p className="mt-1 text-xs text-[#5E5F5E] tnum">
                {line.product.base_price
                  ? formatToman(Number(line.product.base_price) * line.quantity)
                  : "استعلام قیمت"}
              </p>
            </div>
          </li>
        ))}
      </ul>

      {!isInquiry && (
        <div className="mt-5 space-y-2 border-t border-border/60 pt-4 text-sm">
          <div className="flex items-center justify-between text-[#5E5F5E]">
            <span>جمع کل</span>
            <span className="tnum">{formatToman(total)}</span>
          </div>
          <div className="flex items-center justify-between font-bold text-foreground">
            <span>مبلغ قابل پرداخت</span>
            <span className="tnum">{formatToman(total)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
