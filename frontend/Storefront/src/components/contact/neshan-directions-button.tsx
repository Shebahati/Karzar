import { Discovery } from "react-iconly";
import { cn } from "@/lib/utils";
import { STORE_NESHAN_DIRECTIONS_URL } from "@/lib/store-location";

type NeshanDirectionsButtonProps = {
  className?: string;
  /** Dark footer / charcoal surfaces */
  tone?: "light" | "dark";
  size?: "md" | "lg";
};

/**
 * Premium CTA — opens Neshan routing to the KarZar store (new tab).
 */
export function NeshanDirectionsButton({
  className,
  tone = "light",
  size = "md",
}: NeshanDirectionsButtonProps) {
  const isDark = tone === "dark";
  const isLg = size === "lg";

  return (
    <a
      href={STORE_NESHAN_DIRECTIONS_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "group relative inline-flex items-center justify-center gap-2.5 overflow-hidden rounded-xl font-bold transition-all duration-300",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2",
        "active:scale-[0.98]",
        isLg ? "h-12 px-6 text-[15px]" : "h-11 px-5 text-sm",
        isDark
          ? "bg-gradient-to-l from-primary to-[#b01e22] text-white shadow-[0_10px_28px_-12px_rgba(208,35,39,0.65)] hover:shadow-[0_14px_32px_-10px_rgba(208,35,39,0.75)] hover:brightness-105"
          : "bg-gradient-to-l from-primary to-[#b01e22] text-white shadow-soft hover:shadow-card hover:brightness-[1.03]",
        className,
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(105deg,transparent_40%,rgba(255,255,255,0.18)_50%,transparent_60%)] opacity-0 transition-opacity duration-500 group-hover:opacity-100"
      />
      <span
        className={cn(
          "relative grid shrink-0 place-items-center rounded-lg bg-white/15 transition-transform duration-300 group-hover:scale-105",
          isLg ? "h-8 w-8" : "h-7 w-7",
        )}
      >
        <Discovery set="bold" size={isLg ? "medium" : "small"} />
      </span>
      <span className="relative">مسیریابی با نشان</span>
    </a>
  );
}
