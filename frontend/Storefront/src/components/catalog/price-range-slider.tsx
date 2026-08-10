"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { cn, formatNumber, toEnglishDigits } from "@/lib/utils";
import { DEFAULT_MAX_PRICE, DEFAULT_MIN_PRICE } from "@/components/catalog/use-catalog-params";
import { priceRangeStep } from "@/components/catalog/use-catalog-price-domain";

/** Dual-thumb price range with synced numeric inputs. */
export function PriceRangeSlider({
  minValue,
  maxValue,
  onCommit,
  absoluteMin = DEFAULT_MIN_PRICE,
  absoluteMax = DEFAULT_MAX_PRICE,
  disabled = false,
}: {
  minValue: number;
  maxValue: number;
  onCommit: (min: number, max: number) => void;
  absoluteMin?: number;
  absoluteMax?: number;
  disabled?: boolean;
}) {
  const id = useId();
  const span = Math.max(0, absoluteMax - absoluteMin);
  const step = useMemo(
    () => priceRangeStep(absoluteMin, absoluteMax),
    [absoluteMin, absoluteMax],
  );
  const minGap = span <= 0 ? 0 : Math.min(step, span);

  const clampPair = useCallback(
    (a: number, b: number) => {
      const lo = Math.min(absoluteMax, Math.max(absoluteMin, Math.min(a, b)));
      const hi = Math.min(absoluteMax, Math.max(absoluteMin, Math.max(a, b)));
      return { lo, hi };
    },
    [absoluteMin, absoluteMax],
  );

  const initial = clampPair(minValue, maxValue);
  const [lo, setLo] = useState(initial.lo);
  const [hi, setHi] = useState(initial.hi);
  // Refs so mouseup/touchend commit the value just written in onChange (not stale state).
  const loRef = useRef(initial.lo);
  const hiRef = useRef(initial.hi);
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const next = clampPair(minValue, maxValue);
    setLo(next.lo);
    setHi(next.hi);
    loRef.current = next.lo;
    hiRef.current = next.hi;
  }, [minValue, maxValue, clampPair]);

  const pct = useCallback(
    (v: number) => (span <= 0 ? 0 : ((v - absoluteMin) / span) * 100),
    [absoluteMin, span],
  );

  const clamp = (v: number) => Math.min(absoluteMax, Math.max(absoluteMin, v));

  const commit = () => onCommit(loRef.current, hiRef.current);

  const parseInput = (raw: string) => {
    const n = Number(toEnglishDigits(raw).replace(/[^\d]/g, "") || "0");
    return clamp(n);
  };

  return (
    <div className={cn("space-y-4", disabled && "pointer-events-none opacity-50")}>
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
          step={step}
          value={lo}
          disabled={disabled || span <= 0}
          onChange={(e) => {
            const next = Math.min(
              clamp(Number(e.target.value)),
              hiRef.current - minGap,
            );
            loRef.current = next;
            setLo(next);
          }}
          onMouseUp={commit}
          onTouchEnd={commit}
          className="pointer-events-none absolute inset-0 z-20 w-full appearance-none bg-transparent [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:bg-steel [&::-webkit-slider-thumb]:shadow-card"
        />
        <input
          aria-label="حداکثر قیمت"
          type="range"
          min={absoluteMin}
          max={absoluteMax}
          step={step}
          value={hi}
          disabled={disabled || span <= 0}
          onChange={(e) => {
            const next = Math.max(
              clamp(Number(e.target.value)),
              loRef.current + minGap,
            );
            hiRef.current = next;
            setHi(next);
          }}
          onMouseUp={commit}
          onTouchEnd={commit}
          className="pointer-events-none absolute inset-0 z-30 w-full appearance-none bg-transparent [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:shadow-card"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          id={`${id}-min`}
          inputMode="numeric"
          disabled={disabled}
          value={formatNumber(lo)}
          onChange={(e) => {
            const next = parseInput(e.target.value);
            loRef.current = next;
            setLo(next);
          }}
          onBlur={() => {
            const a = Math.min(loRef.current, hiRef.current);
            const b = Math.max(loRef.current, hiRef.current);
            loRef.current = a;
            hiRef.current = b;
            setLo(a);
            setHi(b);
            onCommit(a, b);
          }}
          className="h-11 w-full rounded-xl bg-input px-3 text-base outline-none focus:ring-2 focus:ring-steel/20 tnum"
        />
        <span className="shrink-0 text-sm text-steel">تا</span>
        <input
          id={`${id}-max`}
          inputMode="numeric"
          disabled={disabled}
          value={formatNumber(hi)}
          onChange={(e) => {
            const next = parseInput(e.target.value);
            hiRef.current = next;
            setHi(next);
          }}
          onBlur={() => {
            const a = Math.min(loRef.current, hiRef.current);
            const b = Math.max(loRef.current, hiRef.current);
            loRef.current = a;
            hiRef.current = b;
            setLo(a);
            setHi(b);
            onCommit(a, b);
          }}
          className="h-11 w-full rounded-xl bg-input px-3 text-base outline-none focus:ring-2 focus:ring-steel/20 tnum"
        />
      </div>
      <p className={cn("text-[11px] leading-5 text-steel")}>
        از {formatNumber(lo)} تا {formatNumber(hi)} تومان
      </p>
    </div>
  );
}
