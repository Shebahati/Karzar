import * as React from "react";
import { cn } from "@/lib/utils";

/** Labeled form control wrapper with inline error text. Borderless inputs. */
export function Field({
  label,
  error,
  hint,
  className,
  children,
}: {
  label: string;
  error?: string;
  hint?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <label className={cn("block", className)}>
      <span className="mb-1.5 block text-sm font-bold text-foreground">{label}</span>
      {children}
      {error ? (
        <span className="mt-1 block text-xs text-primary">{error}</span>
      ) : hint ? (
        <span className="mt-1 block text-xs text-muted-foreground">{hint}</span>
      ) : null}
    </label>
  );
}

export const fieldInputClass =
  "h-12 w-full rounded-xl bg-input px-4 text-base outline-none transition-shadow focus:ring-2 focus:ring-ring/40";

/** Textareas use 16px text to avoid iOS input zoom (same as fieldInputClass). */
export const fieldTextareaClass =
  "w-full rounded-xl bg-input p-4 text-base outline-none transition-shadow focus:ring-2 focus:ring-ring/40";
