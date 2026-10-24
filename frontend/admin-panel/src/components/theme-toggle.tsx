"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTheme } from "@/components/theme-provider";
import { THEME_LABELS, type ThemeMode } from "@/lib/theme";

export function ThemeToggle() {
  const { mode, setMode } = useTheme();

  return (
    <Select value={mode} onValueChange={(v) => setMode(v as ThemeMode)}>
      <SelectTrigger className="w-[9.5rem]" aria-label="انتخاب پوسته">
        <SelectValue placeholder="پوسته" />
      </SelectTrigger>
      <SelectContent>
        {(Object.keys(THEME_LABELS) as ThemeMode[]).map((key) => (
          <SelectItem key={key} value={key}>{THEME_LABELS[key]}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
