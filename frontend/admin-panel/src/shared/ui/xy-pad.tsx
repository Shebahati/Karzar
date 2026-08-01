"use client";

import { useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import type { HeroPosition } from "@/entities/hero";

function isRtlElement(el: HTMLElement | null): boolean {
  if (!el) return document.documentElement.dir === "rtl";
  return getComputedStyle(el).direction === "rtl";
}

export function XYPad({
  label,
  value,
  onChange,
  className,
}: {
  label: string;
  value: HeroPosition;
  onChange: (value: HeroPosition) => void;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  const setFromPointer = useCallback(
    (clientX: number, clientY: number) => {
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const rtl = isRtlElement(el);
      // X = distance from inline-start (right edge in RTL), matching hero canvas.
      const x = rtl
        ? ((rect.right - clientX) / rect.width) * 100
        : ((clientX - rect.left) / rect.width) * 100;
      const y = ((clientY - rect.top) / rect.height) * 100;
      onChange({
        x: Math.round(Math.min(100, Math.max(0, x))),
        y: Math.round(Math.min(100, Math.max(0, y))),
      });
    },
    [onChange],
  );

  return (
    <div className={cn("flex min-w-0 flex-col gap-2", className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <span className="text-[11px] font-bold tabular-nums text-ink" dir="ltr">
          {value.x}% · {value.y}%
        </span>
      </div>
      <div
        ref={ref}
        role="slider"
        tabIndex={0}
        aria-label={label}
        className="relative h-28 w-full cursor-crosshair overflow-hidden rounded-xl bg-[linear-gradient(45deg,#eee_25%,transparent_25%,transparent_75%,#eee_75%),linear-gradient(45deg,#eee_25%,transparent_25%,transparent_75%,#eee_75%)] bg-[length:16px_16px] bg-[position:0_0,8px_8px] shadow-soft ring-1 ring-inset ring-border"
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId);
          setFromPointer(e.clientX, e.clientY);
        }}
        onPointerMove={(e) => {
          if (e.buttons !== 1) return;
          setFromPointer(e.clientX, e.clientY);
        }}
      >
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-[#5E5F5E]/20" />
        <div
          className="pointer-events-none absolute h-4 w-4 rounded-full border-2 border-white bg-primary shadow-elevated"
          style={{
            insetInlineStart: `${value.x}%`,
            top: `${value.y}%`,
            marginInlineStart: "-8px",
            marginTop: "-8px",
          }}
        />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <NumberMini label="X" value={value.x} onChange={(x) => onChange({ ...value, x })} />
        <NumberMini label="Y" value={value.y} onChange={(y) => onChange({ ...value, y })} />
      </div>
    </div>
  );
}

function NumberMini({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
}) {
  return (
    <label className="flex items-center gap-2 rounded-lg bg-muted/70 px-2 py-1.5 shadow-soft">
      <span className="text-[10px] font-bold text-muted-foreground">{label}</span>
      <input
        type="number"
        min={0}
        max={100}
        value={value}
        onChange={(e) => onChange(Math.min(100, Math.max(0, Number(e.target.value) || 0)))}
        className="w-full bg-transparent text-sm font-bold tabular-nums text-ink outline-none"
        dir="ltr"
      />
    </label>
  );
}
