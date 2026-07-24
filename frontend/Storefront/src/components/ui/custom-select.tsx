"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ChevronDown, TickSquare } from "react-iconly";
import { cn } from "@/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
}

interface CustomSelectProps {
  value: string;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  className?: string;
  "aria-label"?: string;
}

/** Custom dropdown — no native `<select>`. */
export function CustomSelect({
  value,
  onValueChange,
  options,
  placeholder = "انتخاب کنید",
  className,
  ...props
}: CustomSelectProps) {
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(() =>
    Math.max(0, options.findIndex((o) => o.value === value)),
  );
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();
  const selected = options.find((o) => o.value === value);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    if (!open) return;
    setHighlight(Math.max(0, options.findIndex((o) => o.value === value)));
  }, [open, options, value]);

  const selectAt = (index: number) => {
    const opt = options[index];
    if (!opt) return;
    onValueChange(opt.value);
    setOpen(false);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setOpen(false);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      setHighlight((i) => (i + 1) % options.length);
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      setHighlight((i) => (i - 1 + options.length) % options.length);
      return;
    }
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      selectAt(highlight);
      return;
    }
    if (e.key === "Home" && open) {
      e.preventDefault();
      setHighlight(0);
      return;
    }
    if (e.key === "End" && open) {
      e.preventDefault();
      setHighlight(options.length - 1);
    }
  };

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={props["aria-label"]}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={onKeyDown}
        className="flex h-10 w-full items-center justify-between gap-2 rounded-xl bg-card px-4 text-sm font-bold text-foreground shadow-soft outline-none focus:ring-2 focus:ring-ring/40"
      >
        <span className="truncate">{selected?.label ?? placeholder}</span>
        <span className={cn("shrink-0 transition-transform", open && "rotate-180")}>
          <ChevronDown size="small" set="light" />
        </span>
      </button>

      {open && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-50 mt-2 max-h-60 w-full overflow-auto rounded-xl border border-border bg-card p-1 shadow-elevated"
        >
          {options.map((opt, index) => {
            const active = opt.value === value;
            const focused = index === highlight;
            return (
              <li key={opt.value} role="option" aria-selected={active}>
                <button
                  type="button"
                  onMouseEnter={() => setHighlight(index)}
                  onClick={() => {
                    onValueChange(opt.value);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2.5 text-sm font-bold transition-colors",
                    active ? "bg-accent text-primary" : "text-foreground hover:bg-muted",
                    focused && !active && "bg-muted",
                  )}
                >
                  {opt.label}
                  {active && <TickSquare set="bold" size={16} primaryColor="#C22026" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
