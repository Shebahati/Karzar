"use client";

import { useMemo, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Collapsed-by-default accordion section for catalog filters. */
export function AccordionFilter({
  title,
  hint,
  badge,
  defaultOpen = false,
  children,
}: {
  title: string;
  hint?: string;
  badge?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="overflow-hidden rounded-2xl border border-border/40 bg-card shadow-soft">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-3.5 text-start"
      >
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="text-sm font-bold text-foreground">{title}</span>
            {badge ? (
              <span className="rounded-md bg-steel/10 px-1.5 py-0.5 text-[10px] font-bold text-steel">
                {badge}
              </span>
            ) : null}
          </span>
          {hint ? <span className="mt-0.5 block text-[11px] text-steel">{hint}</span> : null}
        </span>
        <span
          className={cn(
            "grid h-8 w-8 place-items-center rounded-lg bg-secondary text-steel transition-transform",
            open && "rotate-180",
          )}
          aria-hidden
        >
          ⌃
        </span>
      </button>
      {open && <div className="border-t border-border/40 px-4 py-3">{children}</div>}
    </section>
  );
}

export function useOpenMap(keys: string[], initiallyOpen: string[] = []) {
  const initial = useMemo(() => new Set(initiallyOpen), [initiallyOpen]);
  const [open, setOpen] = useState(initial);
  return { open, setOpen };
}
