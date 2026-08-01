"use client";

import { Image2 } from "react-iconly";
import { cn } from "@/lib/utils";

/**
 * Premium empty state when a product has no catalog photo.
 * Soft steel wash + vignette + refined Iconly mark — calm, not busy.
 */
export function ProductPlaceholder({
  name,
  sku,
  className,
}: {
  name?: string | null;
  sku?: string | null;
  className?: string;
}) {
  const label = name || sku || "بدون تصویر";

  return (
    <div
      role="img"
      aria-label={label}
      className={cn(
        "relative grid h-full w-full place-items-center overflow-hidden",
        className,
      )}
    >
      {/* Soft tonal wash — steel base, whisper of brand red */}
      <div
        aria-hidden
        className="absolute inset-0"
        style={{
          background: [
            "radial-gradient(ellipse 70% 55% at 72% 18%, rgba(208,35,39,0.07) 0%, transparent 68%)",
            "radial-gradient(ellipse 85% 70% at 50% 42%, rgba(255,255,255,0.55) 0%, transparent 62%)",
            "linear-gradient(165deg, #F1F0EF 0%, #E9E8E7 48%, #E3E2E1 100%)",
          ].join(", "),
        }}
      />

      {/* Soft edge vignette for depth */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 75% 75% at 50% 48%, transparent 45%, rgba(94,95,94,0.07) 100%)",
        }}
      />

      <div className="relative z-[1] flex flex-col items-center gap-3.5 px-5 text-center">
        {/* Soft disc — no ring/border; gives the icon presence */}
        <div
          className={cn(
            "grid h-[3.25rem] w-[3.25rem] place-items-center rounded-full",
            "bg-white/70 shadow-[0_1px_0_rgba(255,255,255,0.9)_inset]",
            "transition-transform duration-300 ease-out group-hover:scale-105",
          )}
        >
          <Image2
            set="bulk"
            size={26}
            primaryColor="#D02327"
            secondaryColor="#5E5F5E"
          />
        </div>

        <div className="flex flex-col items-center gap-2">
          <span
            aria-hidden
            className="h-px w-5 bg-[#D02327]/45"
          />
          <span className="text-[11px] font-medium tracking-[0.18em] text-[#5E5F5E]/70">
            بدون تصویر
          </span>
        </div>
      </div>
    </div>
  );
}
