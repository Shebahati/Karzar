import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

/**
 * Karzar Admin design system.
 *
 * - Borderless-first: separation is achieved with soft elevation shadows, not hard borders.
 * - Moderate radii (8px–12px) for a balance between sharp and pill shapes.
 * - RTL logical properties (ms-, me-, ps-, pe-, start-, end-) ship natively in Tailwind v3.3+,
 *   and automatically flip under `dir="rtl"`.
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
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        ink: "hsl(var(--ink))",
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
        // Raw brand palette for accents, charts, and decorative surfaces.
        karzar: {
          DEFAULT: "#C22026",
          50: "#FCEAEB",
          100: "#F7C9CB",
          200: "#EE9295",
          300: "#E45A5F",
          400: "#D63A40",
          500: "#C22026",
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
      },
      fontFamily: {
        sans: ["var(--font-iranyekan)", "system-ui", "sans-serif"],
        iranyekan: ["var(--font-iranyekan)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        // Soft, layered elevation tokens that replace hard borders.
        soft: "0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06)",
        card: "0 2px 8px rgba(16, 24, 40, 0.05), 0 8px 24px rgba(16, 24, 40, 0.04)",
        elevated: "0 8px 24px rgba(16, 24, 40, 0.08), 0 16px 48px rgba(16, 24, 40, 0.06)",
        floating: "0 16px 48px rgba(16, 24, 40, 0.16)",
        "primary-glow": "0 8px 24px rgba(194, 32, 38, 0.24)",
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
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in": "fade-in 0.25s ease-out",
      },
    },
  },
  plugins: [animate],
};

export default config;
