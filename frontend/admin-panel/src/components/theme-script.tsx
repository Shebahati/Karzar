export function ThemeScript() {
  const script = `(() => {
    try {
      const key = "karzar-admin-theme";
      const stored = localStorage.getItem(key);
      const mode = stored === "dark" || stored === "light" || stored === "system" ? stored : "system";
      const dark = mode === "dark" || (mode === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
      const root = document.documentElement;
      root.classList.toggle("dark", dark);
      root.style.colorScheme = dark ? "dark" : "light";
    } catch (_) {}
  })();`;
  return <script dangerouslySetInnerHTML={{ __html: script }} />;
}
