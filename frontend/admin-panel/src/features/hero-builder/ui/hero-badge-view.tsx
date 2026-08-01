"use client";

import { cn } from "@/lib/utils";
import type { HeroBadge, HeroBadgeKind } from "@/entities/hero";

const KIND_TONES: Record<
  HeroBadgeKind,
  { bg: string; fg: string; ring: string; accent: string }
> = {
  discount: {
    bg: "linear-gradient(135deg,#D02327,#a41a1f)",
    fg: "#fff",
    ring: "rgba(208,35,39,0.35)",
    accent: "#FCEAEB",
  },
  flash_sale: {
    bg: "linear-gradient(135deg,#D02327,#5E5F5E)",
    fg: "#fff",
    ring: "rgba(94,95,94,0.35)",
    accent: "#fff3cd",
  },
  campaign: {
    bg: "linear-gradient(135deg,#2b2b2b,#5E5F5E)",
    fg: "#fff",
    ring: "rgba(43,43,43,0.3)",
    accent: "#D02327",
  },
  new_arrival: {
    bg: "linear-gradient(135deg,#1f6f4a,#2f9e68)",
    fg: "#fff",
    ring: "rgba(47,158,104,0.3)",
    accent: "#e8f7ef",
  },
  limited: {
    bg: "linear-gradient(135deg,#b45309,#d97706)",
    fg: "#fff",
    ring: "rgba(217,119,6,0.3)",
    accent: "#fff7ed",
  },
  free_shipping: {
    bg: "linear-gradient(135deg,#1e3a5f,#3b82a8)",
    fg: "#fff",
    ring: "rgba(59,130,168,0.3)",
    accent: "#e8f2f8",
  },
  trust: {
    bg: "linear-gradient(135deg,#5E5F5E,#3f4040)",
    fg: "#fff",
    ring: "rgba(94,95,94,0.35)",
    accent: "#D02327",
  },
};

export function HeroBadgeView({
  badge,
  selected,
  onSelect,
  inline = false,
}: {
  badge: HeroBadge;
  selected?: boolean;
  onSelect?: () => void;
  inline?: boolean;
}) {
  const tone = KIND_TONES[badge.kind];
  const base = cn(
    "max-w-[220px] select-none text-start shadow-elevated transition-transform",
    !inline && "pointer-events-auto absolute z-20",
    inline && "relative",
  );
  const pos = inline ? {} : { left: `${badge.position.x}%`, top: `${badge.position.y}%` };

  if (badge.style === "ribbon") {
    return (
      <button
        type="button"
        onClick={onSelect}
        className={cn(base, "overflow-hidden rounded-none", selected && "ring-2 ring-white", badge.animated && "hero-badge-shimmer")}
        style={{ ...pos, background: tone.bg, color: tone.fg }}
      >
        <div className="relative px-4 py-2 pe-6">
          <div className="text-[10px] font-bold uppercase tracking-wide opacity-80">{badge.meta}</div>
          <div className="text-sm font-bold leading-tight">{badge.label}</div>
          <span className="absolute end-0 top-0 h-full w-3 bg-black/15 [clip-path:polygon(0_0,100%_50%,0_100%)]" />
        </div>
      </button>
    );
  }

  if (badge.style === "banner") {
    return (
      <button
        type="button"
        onClick={onSelect}
        className={cn(base, "rounded-lg", selected && "ring-2 ring-white", badge.animated && "hero-badge-pulse")}
        style={{ ...pos, background: tone.bg, color: tone.fg }}
      >
        <div className="flex items-center gap-3 px-3 py-2">
          <span className="grid h-8 min-w-8 place-items-center rounded-md bg-white/15 px-2 text-xs font-black">
            {badge.meta ?? "!"}
          </span>
          <span className="text-sm font-bold">{badge.label}</span>
        </div>
      </button>
    );
  }

  if (badge.style === "stamp") {
    return (
      <button
        type="button"
        onClick={onSelect}
        className={cn(
          base,
          "grid h-20 w-20 -rotate-12 place-content-center rounded-full border-[3px] border-dashed text-center",
          selected && "ring-2 ring-white",
          badge.animated && "hero-badge-float",
        )}
        style={{
          ...pos,
          color: tone.fg,
          background: "rgba(0,0,0,0.35)",
          borderColor: tone.accent,
          boxShadow: `0 0 0 4px ${tone.ring}`,
        }}
      >
        <span className="text-[10px] font-bold opacity-80">{badge.meta}</span>
        <span className="px-1 text-[11px] font-black leading-tight">{badge.label}</span>
      </button>
    );
  }

  if (badge.style === "chip") {
    return (
      <button
        type="button"
        onClick={onSelect}
        className={cn(
          base,
          "rounded-full border border-white/25 bg-white/15 px-3 py-1.5 backdrop-blur-md",
          selected && "ring-2 ring-white",
          badge.animated && "hero-badge-shimmer",
        )}
        style={{ ...pos, color: "#fff" }}
      >
        <span className="flex items-center gap-2">
          <span
            className="h-2 w-2 rounded-full"
            style={{ background: tone.accent === "#D02327" ? "#D02327" : "#fff" }}
          />
          <span className="text-xs font-bold">{badge.label}</span>
          {badge.meta ? (
            <span className="rounded-full bg-white/15 px-1.5 py-0.5 text-[10px] font-bold">{badge.meta}</span>
          ) : null}
        </span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        base,
        "rounded-full px-3 py-1.5",
        selected && "ring-2 ring-white",
        badge.animated && "hero-badge-pulse",
      )}
      style={{ ...pos, background: tone.bg, color: tone.fg }}
    >
      <span className="flex items-center gap-2">
        <span className="text-xs font-bold">{badge.label}</span>
        {badge.meta ? (
          <span className="rounded-full bg-black/20 px-2 py-0.5 text-[10px] font-black">{badge.meta}</span>
        ) : null}
      </span>
    </button>
  );
}
