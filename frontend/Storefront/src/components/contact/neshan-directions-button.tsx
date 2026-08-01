import { Discovery } from "react-iconly";
import { cn } from "@/lib/utils";
import { STORE_NESHAN_DIRECTIONS_URL } from "@/lib/store-location";

type NeshanDirectionsButtonProps = {
  className?: string;
  /** Dark footer / charcoal surfaces */
  tone?: "light" | "dark";
  size?: "sm" | "md" | "lg";
};

/**
 * CTA — opens Neshan routing to the KarZar store (new tab).
 */
export function NeshanDirectionsButton({
  className,
  tone = "light",
  size = "md",
}: NeshanDirectionsButtonProps) {
  const isDark = tone === "dark";

  return (
    <a
      href={STORE_NESHAN_DIRECTIONS_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "group inline-flex items-center justify-center gap-2 rounded-lg font-bold",
        "transition-[background-color,box-shadow,transform,opacity] duration-200 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-0",
        "active:scale-[0.98]",
        size === "sm" && "h-9 gap-1.5 px-3.5 text-xs",
        size === "md" && "h-10 gap-2 px-4 text-sm",
        size === "lg" && "h-11 gap-2 px-5 text-[15px]",
        isDark
          ? "bg-primary text-white shadow-btn-primary hover-fine:bg-karzar-600"
          : "bg-primary text-white hover-fine:bg-karzar-600",
        className,
      )}
    >
      <Discovery set="bold" size="small" />
      <span>مسیریابی با نشان</span>
    </a>
  );
}
