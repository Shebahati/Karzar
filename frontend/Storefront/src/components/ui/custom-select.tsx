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

/** Custom dropdown — no native `<select>`. Compact Karzar control (steel ring, soft shadow). */
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
    <div ref={rootRef} className={cn("relative inline-flex max-w-full", className)}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={props["aria-label"]}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={onKeyDown}
        className={cn(
          "inline-flex h-9 max-w-full items-center justify-between gap-1.5 rounded-xl bg-white ps-3 pe-2.5 text-sm font-medium text-foreground",
          "shadow-btn-rest ring-1 ring-inset ring-steel/10 outline-none",
          "transition-[box-shadow,color,ring-color] duration-200",
          "focus-visible:ring-2 focus-visible:ring-primary/35",
          "active:bg-karzar-50",
          open && "text-primary shadow-btn-soft ring-primary/22",
        )}
      >
        <span className="truncate">{selected?.label ?? placeholder}</span>
        <span
          className={cn(
            "shrink-0 transition-transform duration-300 ease-out",
            open && "rotate-180",
          )}
        >
          <ChevronDown
            size="small"
            set="light"
            primaryColor={open ? "#D02327" : "#5E5F5E"}
          />
        </span>
      </button>

      {open && (
        <ul
          id={listId}
          role="listbox"
          className={cn(
            "absolute end-0 z-50 mt-1.5 max-h-60 min-w-full w-max max-w-[16rem] overflow-auto",
            "rounded-xl border border-steel/10 bg-white p-1 shadow-elevated",
          )}
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
                    "flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary/[0.06] font-semibold text-primary"
                      : "text-foreground hover:bg-steel/[0.06]",
                    focused && !active && "bg-steel/[0.06]",
                  )}
                >
                  {opt.label}
                  {active && (
                    <TickSquare set="bold" size={16} primaryColor="#D02327" />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
