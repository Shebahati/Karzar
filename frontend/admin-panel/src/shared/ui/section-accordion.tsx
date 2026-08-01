"use client";

import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Controlled collapsible — no overflow clipping bugs from nested max-height. */
export function PanelSection({
  title,
  hint,
  active,
  onActivate,
  children,
  defaultOpen = false,
}: {
  title: string;
  hint?: string;
  active?: boolean;
  onActivate?: () => void;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div
      className={cn(
        "min-w-0 overflow-hidden rounded-2xl bg-card shadow-soft ring-1 ring-inset",
        active ? "ring-primary/40" : "ring-border/70",
      )}
    >
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-start"
        onClick={() => {
          setOpen((v) => !v);
          onActivate?.();
        }}
      >
        <div className="min-w-0">
          <div className="truncate text-sm font-bold text-ink">{title}</div>
          {hint ? (
            <div className="mt-0.5 truncate text-[11px] text-muted-foreground">{hint}</div>
          ) : null}
        </div>
        <span
          className={cn(
            "grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-muted text-xs font-bold text-muted-foreground transition",
            open && "rotate-180",
          )}
        >
          ▾
        </span>
      </button>
      {open ? (
        <div className="min-w-0 space-y-3 overflow-x-hidden border-t border-border/60 px-3 py-3 sm:space-y-4 sm:px-4 sm:py-4">
          {children}
        </div>
      ) : null}
    </div>
  );
}
