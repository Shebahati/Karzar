"use client";

import type { ReactNode } from "react";
import { TickSquare } from "react-iconly";
import { cn } from "@/lib/utils";

interface CheckboxProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: ReactNode;
  id?: string;
  className?: string;
}

/** Custom checkbox — no native `<input type="checkbox">`. */
export function Checkbox({ checked, onCheckedChange, label, id, className }: CheckboxProps) {
  return (
    <button
      type="button"
      id={id}
      role="checkbox"
      aria-checked={checked}
      onClick={() => onCheckedChange(!checked)}
      className={cn("flex w-full items-center gap-3 text-start text-sm", className)}
    >
      <span
        className={cn(
          "grid h-5 w-5 shrink-0 place-items-center rounded-md border-2 transition-colors",
          checked ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card",
        )}
      >
        {checked && <TickSquare set="bold" size={14} />}
      </span>
      <span className="font-bold text-foreground">{label}</span>
    </button>
  );
}
