"use client";

import { useMemo } from "react";
import { Calendar } from "react-iconly";

import { cn, toPersianDigits } from "@/lib/utils";

const DAYS = Array.from({ length: 31 }, (_, i) => i + 1);
const MONTHS = [
  { value: 1, label: "فروردین" },
  { value: 2, label: "اردیبهشت" },
  { value: 3, label: "خرداد" },
  { value: 4, label: "تیر" },
  { value: 5, label: "مرداد" },
  { value: 6, label: "شهریور" },
  { value: 7, label: "مهر" },
  { value: 8, label: "آبان" },
  { value: 9, label: "آذر" },
  { value: 10, label: "دی" },
  { value: 11, label: "بهمن" },
  { value: 12, label: "اسفند" },
];
const HOURS = Array.from({ length: 24 }, (_, i) => i);
const MINUTES = [0, 15, 30, 45];

interface DateTimePickerProps {
  value: string;
  onChange: (iso: string) => void;
  className?: string;
}

function parseValue(value: string) {
  if (!value) {
    const now = new Date();
    return {
      day: now.getDate(),
      month: now.getMonth() + 1,
      year: now.getFullYear(),
      hour: 10,
      minute: 0,
    };
  }
  const d = new Date(value);
  return {
    day: d.getDate(),
    month: d.getMonth() + 1,
    year: d.getFullYear(),
    hour: d.getHours(),
    minute: d.getMinutes(),
  };
}

function PickerSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: number;
  options: { value: number; label: string }[];
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-1">
      <span className="text-[10px] font-bold text-muted-foreground">{label}</span>
      <div className="flex flex-wrap gap-1">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={cn(
              "rounded-lg px-2 py-1.5 text-xs font-bold transition-colors",
              value === opt.value
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80",
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Custom date/time picker — no native browser controls. */
export function DateTimePicker({ value, onChange, className }: DateTimePickerProps) {
  const parts = useMemo(() => parseValue(value), [value]);

  function emit(next: Partial<typeof parts>) {
    const merged = { ...parts, ...next };
    const iso = new Date(merged.year, merged.month - 1, merged.day, merged.hour, merged.minute).toISOString();
    onChange(iso);
  }

  const display = value ? new Date(value).toLocaleString("fa-IR") : "انتخاب نشده";

  return (
    <div className={cn("space-y-3 rounded-xl border border-border bg-muted/30 p-3", className)}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Calendar set="light" size={16} />
        <span className="tnum">{toPersianDigits(display)}</span>
      </div>

      <PickerSelect
        label="روز"
        value={parts.day}
        options={DAYS.map((d) => ({ value: d, label: toPersianDigits(d) }))}
        onChange={(day) => emit({ day })}
      />

      <PickerSelect
        label="ماه"
        value={parts.month}
        options={MONTHS}
        onChange={(month) => emit({ month })}
      />

      <div className="grid grid-cols-2 gap-2">
        <PickerSelect
          label="ساعت"
          value={parts.hour}
          options={HOURS.map((h) => ({
            value: h,
            label: toPersianDigits(String(h).padStart(2, "0")),
          }))}
          onChange={(hour) => emit({ hour })}
        />
        <PickerSelect
          label="دقیقه"
          value={parts.minute}
          options={MINUTES.map((m) => ({
            value: m,
            label: toPersianDigits(String(m).padStart(2, "0")),
          }))}
          onChange={(minute) => emit({ minute })}
        />
      </div>
    </div>
  );
}
