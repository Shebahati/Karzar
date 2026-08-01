/** Mobile composition recipes — keep in sync with admin `composeHeroForMobile`.
 * Dock is no longer rendered inside the Storefront mobile hero; presets only
 * remap copy / CTA / media. Categories live in the home sheet below the hero.
 */

import type { DesignedHeroConfig } from "@/types/hero-design";

export type MobileComposePreset = "balanced" | "copy-focus" | "media-focus" | "dock-first";

export type MobileDockScale = "sm" | "md" | "lg";

export interface MobileComposeView {
  config: DesignedHeroConfig;
  /** @deprecated Dock removed from mobile hero — kept for admin preview API compat */
  dockScale: MobileDockScale;
  dockPadClass: string;
  dockFadeTall: boolean;
  overlayOpacity: number;
  label: string;
}

export function composeHeroForMobile(
  source: DesignedHeroConfig,
  preset: MobileComposePreset = "balanced",
): MobileComposeView {
  const config = structuredClone(source);
  const buttons = config.buttons;

  switch (preset) {
    case "copy-focus": {
      config.typography.position = { x: 5, y: 14 };
      config.typography.maxWidth = 340;
      config.typography.titleSize = Math.round(
        Math.min(56, Math.max(28, config.typography.titleSize * 1.32)),
      );
      config.typography.subtitleSize = Math.round(config.typography.subtitleSize * 1.14);
      config.typography.align = "start";
      buttons.forEach((b, i) => {
        b.position = { x: 5, y: 48 + i * 11 };
        b.sizePreset = i === 0 ? "lg" : "md";
      });
      config.badges = [];
      config.carousel.enabled = false;
      config.overlay.opacity = Math.min(0.78, Math.max(0.5, config.overlay.opacity + 0.14));
      return {
        config,
        dockScale: "sm",
        dockPadClass: "pb-2 pt-10",
        dockFadeTall: false,
        overlayOpacity: config.overlay.opacity,
        label: "تمرکز متن",
      };
    }
    case "media-focus": {
      config.typography.position = { x: 6, y: 52 };
      config.typography.maxWidth = 280;
      config.typography.titleSize = Math.round(config.typography.titleSize * 0.78);
      config.typography.subtitleSize = Math.max(
        11,
        Math.round(config.typography.subtitleSize * 0.82),
      );
      config.typography.align = "start";
      config.buttons = buttons.slice(0, 1).map((b) => ({
        ...b,
        position: { x: 6, y: 72 },
        stylePreset: "on-dark-glass" as const,
        sizePreset: "sm" as const,
      }));
      config.badges = [];
      config.carousel.enabled = false;
      config.overlay.opacity = Math.max(0.18, config.overlay.opacity * 0.48);
      return {
        config,
        dockScale: "sm",
        dockPadClass: "pb-2 pt-12",
        dockFadeTall: false,
        overlayOpacity: config.overlay.opacity,
        label: "تمرکز تصویر",
      };
    }
    case "dock-first": {
      // Legacy id — was dock-priority; dock moved out of mobile hero → compact copy layout
      config.typography.position = { x: 6, y: 16 };
      config.typography.maxWidth = 300;
      config.typography.titleSize = Math.round(config.typography.titleSize * 0.88);
      config.typography.subtitleSize = Math.max(
        12,
        Math.round(config.typography.subtitleSize * 0.92),
      );
      config.typography.align = "start";
      config.buttons = buttons.slice(0, 2).map((b, i) => ({
        ...b,
        position: { x: 6, y: 42 + i * 12 },
        sizePreset: i === 0 ? ("md" as const) : ("sm" as const),
      }));
      config.badges = [];
      config.carousel.enabled = false;
      config.overlay.opacity = Math.min(0.62, Math.max(0.36, config.overlay.opacity));
      return {
        config,
        dockScale: "sm",
        dockPadClass: "pb-2 pt-10",
        dockFadeTall: false,
        overlayOpacity: config.overlay.opacity,
        label: "چیدمان فشرده",
      };
    }
    case "balanced":
    default: {
      config.typography.position = { x: 6, y: 16 };
      config.typography.maxWidth = 300;
      config.typography.titleSize = Math.round(config.typography.titleSize * 0.95);
      config.typography.align = "start";
      buttons.forEach((b, i) => {
        b.position = { x: 6, y: 42 + i * 11 };
        b.sizePreset = "md";
      });
      config.badges.forEach((badge, i) => {
        badge.position = { x: 6 + i * 2, y: 6 + i * 5 };
      });
      if (config.carousel?.enabled) {
        config.carousel.position = { x: 4, y: 62 };
        config.carousel.layoutPreset = "row-compact";
        config.carousel.maxItems = Math.min(3, config.carousel.maxItems);
      }
      return {
        config,
        dockScale: "md",
        dockPadClass: "pb-3 pt-14",
        dockFadeTall: false,
        overlayOpacity: config.overlay.opacity,
        label: "متعادل",
      };
    }
  }
}
