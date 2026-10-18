"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  calculateProductDiscount,
  type CalculatedDiscount,
} from "@/features/catalog/discount-pricing";

interface Props {
  basePrice: string;
  originalPrice: string;
  onApply: (result: CalculatedDiscount) => void;
}

export function ProductDiscountCalculator({ basePrice, originalPrice, onApply }: Props) {
  const [percent, setPercent] = useState("");
  let result: CalculatedDiscount | null = null;
  let error: string | null = null;

  if (percent.trim()) {
    try {
      result = calculateProductDiscount(basePrice ?? "", originalPrice ?? "", percent);
    } catch (err) {
      error = err instanceof Error ? err.message : "محاسبه تخفیف نامعتبر است.";
    }
  }

  return (
    <div className="rounded-xl border border-input p-4 space-y-3">
      <Field
        label="درصد تخفیف (٪)"
        htmlFor="discount_percent_calculator"
        hint="فقط محاسبه‌گر فرم است؛ قیمت نهایی با ذخیره تغییرات ثبت می‌شود."
        error={error ?? undefined}
      >
        <Input
          id="discount_percent_calculator"
          dir="ltr"
          inputMode="decimal"
          placeholder="مثلاً 15"
          value={percent}
          onChange={(event) => setPercent(event.target.value)}
          aria-invalid={Boolean(error)}
        />
      </Field>
      {result && (
        <p className="text-sm" role="status">
          قیمت قبل از تخفیف: {result.originalPrice} تومان؛ قیمت فروش: {result.basePrice} تومان
        </p>
      )}
      <Button
        type="button"
        variant="outline"
        disabled={!result}
        onClick={() => {
          if (result) {
            onApply(result);
            setPercent("");
          }
        }}
      >
        اعمال در فرم
      </Button>
      <p className="text-xs text-muted-foreground">
        در صورت وجود تخفیف قبلی، مبنا قیمت قبل از تخفیف است، نه قیمت فروش فعلی.
        اعمال در فرم به‌تنهایی ذخیره نمی‌کند.
      </p>
    </div>
  );
}
