import localFont from "next/font/local";

/**
 * IRANYekanX via next/font — self-hosted, preloaded, weight-subsetted.
 * Light (300) omitted: UI uses 400/500/700 only (see Tailwind font-*).
 * Dana files under public/fonts/ are unused leftovers and intentionally not loaded.
 */
export const iranYekan = localFont({
  src: [
    {
      path: "../../public/fonts/IRANYekanX-Regular.woff2",
      weight: "400",
      style: "normal",
    },
    {
      path: "../../public/fonts/IRANYekanX-Medium.woff2",
      weight: "500",
      style: "normal",
    },
    {
      path: "../../public/fonts/IRANYekanX-Bold.woff2",
      weight: "700",
      style: "normal",
    },
  ],
  variable: "--font-iranyekan",
  display: "swap",
  preload: true,
  fallback: ["Tahoma", "Arial", "sans-serif"],
  adjustFontFallback: false,
});
