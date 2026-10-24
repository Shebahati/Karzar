export type ThemeMode = "light" | "dark" | "system";

export const THEME_STORAGE_KEY = "karzar-admin-theme";

export function resolveTheme(mode: ThemeMode): "light" | "dark" {
  if (mode === "dark") return "dark";
  if (mode === "light") return "light";
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export const THEME_LABELS: Record<ThemeMode, string> = {
  light: "روشن",
  dark: "تاریک",
  system: "مطابق سیستم",
};
