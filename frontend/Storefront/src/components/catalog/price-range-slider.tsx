"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { cn, formatNumber, toEnglishDigits, toPersianDigits } from "@/lib/utils";
import { DEFAULT_MAX_PRICE, DEFAULT_MIN_PRICE } from "@/components/catalog/use-catalog-params";

/** Dual-thumb price range with synced numeric inputs. */
export function PriceRangeSlider({
  minValue,
  maxValue,
  onCommit,
  absoluteMin = DEFAULT_MIN_PRICE,
  absoluteMax = DEFAULT_MAX_PRICE,
}: {
  minValue: number;
  maxValue: number;
  onCommit: (min: number, max: number) => void;
  absoluteMin?: number;
  absoluteMax?: number;
}) {
  const id = useId();
  const [lo, setLo] = useState(minValue);
  const [hi, setHi] = useState(maxValue);
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLo(minValue);
    setHi(maxValue);
  }, [minValue, maxValue]);

  const pct = useCallback(
    (v: number) => ((v - absoluteMin) / (absoluteMax - absoluteMin)) * 100,
    [absoluteMin, absoluteMax],
  );

  const clamp = (v: number) => Math.min(absoluteMax, Math.max(absoluteMin, v));

  return (
    <div className="space-y-4">
      <div ref={trackRef} className="relative h-8 touch-none px-1">
        <div className="absolute inset-x-1 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-secondary" />
        <div
          className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-steel/70"
          style={{
            right: `${pct(lo)}%`,
            left: `${100 - pct(hi)}%`,
          }}
        />
        <input
          aria-label="حداقل قیمت"
          type="range"
          min={absoluteMin}
          max={absoluteMax}
          step={100_000}
          value={lo}
          onChange={(e) => {
            const next = clamp(Number(e.target.value));
            setLo(Math.min(next, hi - 100_000));
          }}
          onMouseUp={() => onCommit(lo, hi)}
          onTouchEnd={() => onCommit(lo, hi)}
          className="pointer-events-none absolute inset-0 z-20 w-full appearance-none bg-transparent [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:bg-steel [&::-webkit-slider-thumb]:shadow-card"
        />
        <input
          aria-label="حداکثر قیمت"
          type="range"
          min={absoluteMin}
          max={absoluteMax}
          step={100_000}
          value={hi}
          onChange={(e) => {
            const next = clamp(Number(e.target.value));
            setHi(Math.max(next, lo + 100_000));
          }}
          onMouseUp={() => onCommit(lo, hi)}
          onTouchEnd={() => onCommit(lo, hi)}
          className="pointer-events-none absolute inset-0 z-30 w-full appearance-none bg-transparent [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:shadow-card"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          id={`${id}-min`}
          inputMode="numeric"
          value={toPersianDigits(String(lo))}
          onChange={(e) => {
            const n = Number(toEnglishDigits(e.target.value).replace(/[^\d]/g, "") || "0");
            setLo(clamp(n));
          }}
          onBlur={() => onCommit(Math.min(lo, hi), Math.max(lo, hi))}
          className="h-11 w-full rounded-xl bg-input px-3 text-sm outline-none focus:ring-2 focus:ring-steel/20 tnum"
        />
        <span className="shrink-0 text-sm text-steel">تا</span>
        <input
          id={`${id}-max`}
          inputMode="numeric"
          value={toPersianDigits(String(hi))}
          onChange={(e) => {
            const n = Number(toEnglishDigits(e.target.value).replace(/[^\d]/g, "") || "0");
            setHi(clamp(n));
          }}
          onBlur={() => onCommit(Math.min(lo, hi), Math.max(lo, hi))}
          className="h-11 w-full rounded-xl bg-input px-3 text-sm outline-none focus:ring-2 focus:ring-steel/20 tnum"
        />
      </div>
      <p className={cn("text-[11px] leading-5 text-steel")}>
        از {formatNumber(lo)} تا {formatNumber(hi)} تومان
      </p>
    </div>
  );
}
