"use client";

import Image from "next/image";
import { formatToman } from "@/lib/utils";
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
              {line.product.thumbnail ? (
                <Image
                  src={line.product.thumbnail}
                  alt={line.product.name}
                  fill
                  sizes="56px"
                  className="object-contain p-1"
                />
              ) : (
                <span className="grid h-full w-full place-items-center text-sm font-medium">
                  {(line.product.name || "ک").slice(0, 1)}
                </span>
              )}
              <span className="absolute -top-1 -start-1 grid h-5 min-w-5 place-items-center rounded-full bg-primary px-1 text-[11px] font-medium text-primary-foreground tnum">
                {line.quantity}
              </span>
            </div>
            <div className="min-w-0 flex-1">
              <p className="line-clamp-1 text-sm font-bold text-foreground">
                {line.product.name}
              </p>
              <p className="text-xs text-muted-foreground tnum">
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
          <div className="flex items-center justify-between text-muted-foreground">
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
