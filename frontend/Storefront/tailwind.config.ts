import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";
import logical from "tailwindcss-logical";

/**
 * Karzar Storefront design system.
 *
 * Adapted from the admin-panel config for 100% visual consistency:
 * - Borderless-first: separation via soft elevation shadows, not hard borders.
 * - RTL logical properties (ms-, me-, ps-, pe-, start-, end-) flip under dir="rtl".
 * - The `tailwindcss-logical` plugin adds extra logical utilities for the storefront.
 */
const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/features/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1.25rem",
      screens: { "2xl": "1320px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        steel: {
          DEFAULT: "hsl(var(--steel))",
          foreground: "hsl(var(--steel-foreground))",
        },
        karzar: {
          DEFAULT: "#D02327",
          50: "#FCEAEB",
          100: "#F7C9CB",
          200: "#EE9295",
          300: "#E45A5F",
          400: "#D63A40",
          500: "#D02327",
          600: "#A41A1F",
          700: "#7E1418",
          800: "#590E11",
          900: "#33080A",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "calc(var(--radius) + 4px)",
        "2xl": "calc(var(--radius) + 8px)",
      },
      fontFamily: {
        sans: ["var(--font-iranyekan)", "system-ui", "sans-serif"],
        iranyekan: ["var(--font-iranyekan)", "system-ui", "sans-serif"],
      },
      spacing: {
        13: "3.25rem",
        18: "4.5rem",
        /** FE-001 shared section rhythm (see globals.css :root). */
        "section-y": "var(--space-section-y)",
        "section-gap": "var(--space-section-gap)",
      },
      fontSize: {
        section: [
          "var(--type-section)",
          { lineHeight: "1.35", fontWeight: "700" },
        ],
        "section-lg": [
          "var(--type-section-lg)",
          { lineHeight: "1.3", fontWeight: "700" },
        ],
        lede: ["var(--type-lede)", { lineHeight: "var(--leading-lede)" }],
        "lede-lg": [
          "var(--type-lede-lg)",
          { lineHeight: "var(--leading-lede-lg)" },
        ],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06)",
        card: "0 2px 8px rgba(16, 24, 40, 0.05), 0 8px 24px rgba(16, 24, 40, 0.04)",
        elevated: "0 8px 24px rgba(16, 24, 40, 0.08), 0 16px 48px rgba(16, 24, 40, 0.06)",
        floating: "0 16px 48px rgba(16, 24, 40, 0.16)",
        "primary-glow": "0 8px 24px rgba(194, 32, 38, 0.16)",
        glass: "0 8px 32px rgba(94, 95, 94, 0.12)",
        /** Button rest / hover — brand-tinted, no white bloom */
        "btn-rest": "0 1px 2px rgba(94, 95, 94, 0.06)",
        "btn-primary": "0 6px 16px -6px rgba(208, 35, 39, 0.42)",
        "btn-soft": "0 6px 14px -8px rgba(208, 35, 39, 0.28)",
        "btn-steel": "0 4px 12px -6px rgba(94, 95, 94, 0.2)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(-100%)" },
        },
        "marquee-rtl": {
          from: { transform: "translateX(0)" },
          to: { transform: "translateX(50%)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in": "fade-in 0.25s ease-out",
        marquee: "marquee-rtl 30s linear infinite",
      },
    },
  },
  plugins: [
    animate,
    logical,
    /** Real pointer hover only — avoids sticky “glow” after tap on touch devices */
    function hoverFineVariant({
      addVariant,
    }: {
      addVariant: (name: string, definition: string) => void;
    }) {
      addVariant(
        "hover-fine",
        "@media (hover: hover) and (pointer: fine) { &:hover }",
      );
    },
  ],
};

export default config;
