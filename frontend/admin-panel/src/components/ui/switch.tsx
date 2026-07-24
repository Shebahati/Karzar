"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

export interface SwitchProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
  "aria-label"?: string;
}

/**
 * Lightweight controlled toggle (no extra Radix dependency). Logical insets
 * (`start-`) keep the thumb correctly positioned under RTL.
 */
const Switch = React.forwardRef<HTMLButtonElement, SwitchProps>(
  ({ checked, onCheckedChange, disabled, id, ...props }, ref) => {
    return (
      <button
        type="button"
        role="switch"
        id={id}
        ref={ref}
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onCheckedChange(!checked)}
        className={cn(
          "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          checked ? "bg-primary" : "bg-muted-foreground/30",
        )}
        {...props}
      >
        <span
          className={cn(
            "pointer-events-none absolute top-1/2 h-5 w-5 -translate-y-1/2 rounded-full bg-white shadow-soft transition-all duration-200",
            checked ? "start-1" : "end-1",
          )}
        />
      </button>
    );
  },
);
Switch.displayName = "Switch";

export { Switch };
