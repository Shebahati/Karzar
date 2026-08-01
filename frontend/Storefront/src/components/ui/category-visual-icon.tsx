"use client";

import type { ComponentType } from "react";
import * as Icons from "react-iconly";
import { Category as CategoryIcon } from "react-iconly";
import { isCategoryIconUrl } from "@/config/category-icons";
import { cn } from "@/lib/utils";

type IconlyProps = {
  size?: number | string;
  set?: string;
  primaryColor?: string;
  stroke?: string;
};

/**
 * Renders a category icon: designed PNG/URL when provided, otherwise Iconly by name.
 * `overflowTop` intentionally lets the asset poke above the parent circle (hero dock).
 */
export function CategoryVisualIcon({
  icon,
  size = 22,
  color = "#5E5F5E",
  className,
  imgClassName,
  overflowTop = false,
  /** Multiplier when overflowTop (default ~2.02×). Hero dock may bump further. */
  overflowScale = 2.015,
  alt = "",
}: {
  icon?: string | null;
  size?: number;
  color?: string;
  className?: string;
  imgClassName?: string;
  /** Scale up; centered in parent circle with a tiny upward peek. */
  overflowTop?: boolean;
  overflowScale?: number;
  alt?: string;
}) {
  if (isCategoryIconUrl(icon)) {
    // Circles stay sized by the parent; only the glyph grows / nudges.
    const imgSize = overflowTop ? Math.round(size * overflowScale) : size;
    // Absolute flex center keeps the glyph dead-center in the circle (avoids
    // left-stuck replaced-element / RTL quirks). Tiny -translate-y peeks top.
    if (overflowTop) {
      return (
        <span
          className={cn(
            "pointer-events-none absolute inset-0 flex items-center justify-center overflow-visible",
            className,
          )}
          aria-hidden={alt ? undefined : true}
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- dynamic category CDN/local URLs */}
          <img
            src={icon!}
            alt={alt}
            width={imgSize}
            height={imgSize}
            className={cn(
              "mx-auto block select-none object-contain object-center",
              "-translate-y-[8%] drop-shadow-[0_6px_12px_rgba(0,0,0,0.28)]",
              imgClassName,
            )}
            style={{ width: imgSize, height: imgSize, maxWidth: "none" }}
            draggable={false}
          />
        </span>
      );
    }
    return (
      // eslint-disable-next-line @next/next/no-img-element -- dynamic category CDN/local URLs
      <img
        src={icon!}
        alt={alt}
        width={imgSize}
        height={imgSize}
        className={cn(
          "pointer-events-none mx-auto block select-none object-contain object-center",
          imgClassName,
          className,
        )}
        style={{ width: imgSize, height: imgSize, maxWidth: "none" }}
        draggable={false}
      />
    );
  }

  const name = icon?.trim() || "Category";
  const Cmp = (Icons as Record<string, unknown>)[name] as ComponentType<IconlyProps> | undefined;
  if (!Cmp) {
    return (
      <span className={className}>
        <CategoryIcon size={size} set="light" primaryColor={color} stroke="light" />
      </span>
    );
  }
  return (
    <span className={className}>
      <Cmp size={size} set="light" primaryColor={color} stroke="light" />
    </span>
  );
}
