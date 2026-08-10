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
  // Refs so mouseup/touchend commit the value just written in onChange (not stale state).
  const loRef = useRef(minValue);
  const hiRef = useRef(maxValue);
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLo(minValue);
    setHi(maxValue);
    loRef.current = minValue;
    hiRef.current = maxValue;
  }, [minValue, maxValue]);

  const pct = useCallback(
    (v: number) => ((v - absoluteMin) / (absoluteMax - absoluteMin)) * 100,
    [absoluteMin, absoluteMax],
  );

  const clamp = (v: number) => Math.min(absoluteMax, Math.max(absoluteMin, v));

  const commit = () => onCommit(loRef.current, hiRef.current);

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
            const next = Math.min(clamp(Number(e.target.value)), hiRef.current - 100_000);
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
          step={100_000}
          value={hi}
          onChange={(e) => {
            const next = Math.max(clamp(Number(e.target.value)), loRef.current + 100_000);
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
          value={toPersianDigits(String(lo))}
          onChange={(e) => {
            const n = Number(toEnglishDigits(e.target.value).replace(/[^\d]/g, "") || "0");
            const next = clamp(n);
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
          value={toPersianDigits(String(hi))}
          onChange={(e) => {
            const n = Number(toEnglishDigits(e.target.value).replace(/[^\d]/g, "") || "0");
            const next = clamp(n);
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
