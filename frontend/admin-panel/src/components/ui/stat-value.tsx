import { cn } from "@/lib/utils";

interface StatValueProps {
  value: string;
  className?: string;
}

/** Count Western + Persian digits to pick a size that fits long Toman totals. */
function digitLength(value: string): number {
  return (value.match(/[0-9۰-۹]/g) ?? []).length;
}

/**
 * Dashboard/report metric number. Scales down for long Toman figures and never
 * truncates — `truncate` + fixed text-xl was clipping Hesabfa/website sales.
 */
export function StatValue({ value, className }: StatValueProps) {
  const digits = digitLength(value);
  const sizeClass =
    digits >= 14
      ? "text-sm sm:text-[0.9375rem]"
      : digits >= 11
        ? "text-[0.9375rem] sm:text-base"
        : digits >= 8
          ? "text-base sm:text-lg"
          : "text-lg sm:text-xl";

  return (
    <span
      className={cn(
        "block w-full max-w-full break-words font-bold leading-snug text-ink tnum",
        sizeClass,
        className,
      )}
      dir="rtl"
      lang="fa"
      title={value}
    >
      {value}
    </span>
  );
}
