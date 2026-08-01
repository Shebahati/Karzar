"use client";

import { ColorField } from "./color-field";

export function GradientBuilder({
  from,
  to,
  angle,
  onFrom,
  onTo,
  onAngle,
}: {
  from: string;
  to: string;
  angle: number;
  onFrom: (v: string) => void;
  onTo: (v: string) => void;
  onAngle: (v: number) => void;
}) {
  return (
    <div className="space-y-3">
      <div
        className="h-16 rounded-xl shadow-soft ring-1 ring-inset ring-border"
        style={{ background: `linear-gradient(${angle}deg, ${from}, ${to})` }}
      />
      <ColorField label="شروع گرادیان" value={from} onChange={onFrom} allowAlpha />
      <ColorField label="پایان گرادیان" value={to} onChange={onTo} allowAlpha />
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">زاویه</span>
          <span className="rounded-md bg-muted px-2 py-0.5 text-[11px] font-bold tabular-nums text-ink">
            {angle}°
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={360}
          step={1}
          value={angle}
          onChange={(e) => onAngle(Number(e.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-full bg-border accent-primary"
        />
        <div className="flex flex-wrap gap-1.5">
          {[0, 45, 90, 135, 180, 225, 270].map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => onAngle(a)}
              className={`rounded-lg px-2 py-1 text-[10px] font-bold ${
                angle === a ? "bg-ink text-white" : "bg-muted text-ink"
              }`}
            >
              {a}°
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
