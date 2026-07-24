import { cn } from "@/lib/utils";

/**
 * Karzar brand mark for the admin panel. No shared logo asset exists in this
 * app yet, so this renders a lightweight inline SVG monogram (abstract "K"
 * built from two angled strokes, echoing a wrench/tool motif) instead of a
 * plain single letter glyph. Swap the `<svg>` below for a real asset once
 * the storefront logo file is published to `public/`.
 */
export function LogoMark({ className, size = 24 }: { className?: string; size?: number }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      className={cn("shrink-0", className)}
      aria-hidden="true"
    >
      <path
        d="M5 3.5v17"
        stroke="currentColor"
        strokeWidth={2.4}
        strokeLinecap="round"
      />
      <path
        d="M6 12.2 15.5 4M6 11.8 15.5 20"
        stroke="currentColor"
        strokeWidth={2.4}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="18.2" cy="12" r="1.6" fill="currentColor" />
    </svg>
  );
}
