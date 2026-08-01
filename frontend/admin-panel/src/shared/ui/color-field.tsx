"use client";

import { BRAND_COLOR_PRESETS } from "@/entities/hero";
import { cn } from "@/lib/utils";

function parseColor(value: string): { r: number; g: number; b: number; a: number } {
  const v = value.trim();
  const rgba = v.match(
    /^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([0-9.]+))?\s*\)$/i,
  );
  if (rgba) {
    return {
      r: Number(rgba[1]),
      g: Number(rgba[2]),
      b: Number(rgba[3]),
      a: rgba[4] != null ? Number(rgba[4]) : 1,
    };
  }
  let hex = v;
  if (hex.startsWith("#") && hex.length === 4) {
    hex = `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`;
  }
  if (hex.startsWith("#") && hex.length === 7) {
    return {
      r: parseInt(hex.slice(1, 3), 16),
      g: parseInt(hex.slice(3, 5), 16),
      b: parseInt(hex.slice(5, 7), 16),
      a: 1,
    };
  }
  return { r: 208, g: 35, b: 39, a: 1 };
}

function toHex({ r, g, b }: { r: number; g: number; b: number }) {
  const h = (n: number) => n.toString(16).padStart(2, "0");
  return `#${h(r)}${h(g)}${h(b)}`;
}

function toCss(r: number, g: number, b: number, a: number) {
  if (a >= 0.995) return toHex({ r, g, b });
  return `rgba(${r},${g},${b},${Math.round(a * 100) / 100})`;
}

export function ColorField({
  label,
  value,
  onChange,
  className,
  showPresets = true,
  allowAlpha = true,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  className?: string;
  showPresets?: boolean;
  allowAlpha?: boolean;
}) {
  const parsed = parseColor(value);
  const hex = toHex(parsed);
  const opacityPct = Math.round(parsed.a * 100);

  return (
    <label className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <div className="flex min-w-0 items-center gap-2 rounded-xl bg-muted/60 p-1.5">
        <input
          type="color"
          value={hex}
          onChange={(e) => {
            const next = parseColor(e.target.value);
            onChange(toCss(next.r, next.g, next.b, allowAlpha ? parsed.a : 1));
          }}
          className="h-9 w-11 shrink-0 cursor-pointer overflow-hidden rounded-lg border-0 bg-transparent p-0"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-9 min-w-0 flex-1 rounded-lg bg-card px-2.5 text-xs font-medium text-ink outline-none ring-1 ring-inset ring-border focus:ring-primary/30 sm:text-sm"
          dir="ltr"
          placeholder="#D02327"
        />
      </div>
      {allowAlpha ? (
        <div className="flex min-w-0 items-center gap-2">
          <span className="shrink-0 text-[10px] font-bold text-muted-foreground">شفافیت</span>
          <input
            type="range"
            min={0}
            max={100}
            value={opacityPct}
            onChange={(e) => {
              const a = Number(e.target.value) / 100;
              onChange(toCss(parsed.r, parsed.g, parsed.b, a));
            }}
            className="h-1.5 min-w-0 flex-1 appearance-none rounded-full bg-border accent-primary"
          />
          <span className="w-10 shrink-0 text-end text-[10px] font-bold tabular-nums text-ink">
            {opacityPct}%
          </span>
        </div>
      ) : null}
      {showPresets ? (
        <div className="flex flex-wrap gap-1.5 pt-0.5">
          {BRAND_COLOR_PRESETS.map((c) => (
            <button
              key={c}
              type="button"
              title={c}
              onClick={() => onChange(c)}
              className={cn(
                "h-6 w-6 rounded-md ring-1 ring-black/10 transition hover:scale-110",
                value.toLowerCase() === c.toLowerCase() && "ring-2 ring-primary",
              )}
              style={{ background: c }}
            />
          ))}
        </div>
      ) : null}
    </label>
  );
}
