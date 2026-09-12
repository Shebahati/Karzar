"use client";

import { formatToman, toPersianDigits } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { ShippingQuoteOption } from "@/types/shipping";

export function ShippingOptions({
  options,
  selectedToken,
  loading,
  error,
  onSelect,
}: {
  options: ShippingQuoteOption[];
  selectedToken: string | null;
  loading: boolean;
  error: string | null;
  onSelect: (option: ShippingQuoteOption) => void;
}) {
  if (loading) {
    return (
      <p className="mt-3 text-sm text-muted-foreground" role="status">
        در حال محاسبه هزینه ارسال…
      </p>
    );
  }
  if (error) {
    return (
      <p className="mt-3 text-sm text-destructive" role="alert">
        {error}
      </p>
    );
  }
  if (!options.length) {
    return (
      <p className="mt-3 text-sm text-muted-foreground">
        پس از انتخاب شهر مقصد، گزینه‌های ارسال نمایش داده می‌شود.
      </p>
    );
  }
  return (
    <div className="mt-4 space-y-2" role="radiogroup" aria-label="انتخاب سرویس ارسال">
      {options.map((option) => {
        const active = selectedToken === option.quote_token;
        return (
          <button
            key={option.quote_token}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onSelect(option)}
            className={cn(
              "w-full rounded-xl border px-4 py-3 text-start transition-colors",
              active ? "border-primary/40 bg-accent" : "border-border/50 bg-background hover:border-steel/30",
            )}
          >
            <span className="flex items-center justify-between gap-3">
              <span className="font-bold text-foreground">{option.title}</span>
              <span className="tnum text-sm font-bold">{formatToman(option.amount_toman)}</span>
            </span>
            {option.eta && (
              <span className="mt-1 block text-xs text-steel">
                زمان تقریبی: {toPersianDigits(option.eta)}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
