"use client";

import { cn } from "@/lib/utils";

export function OpacitySlider({
  label,
  value,
  onChange,
  min = 0,
  max = 1,
  step = 0.01,
  className,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  className?: string;
}) {
  const pct = Math.round(((value - min) / (max - min)) * 100);
  return (
    <label className={cn("flex flex-col gap-2", className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <span className="rounded-md bg-muted px-2 py-0.5 text-[11px] font-bold tabular-nums text-ink">
          {pct}%
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-border accent-primary"
      />
    </label>
  );
}
