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
  alt = "",
}: {
  icon?: string | null;
  size?: number;
  color?: string;
  className?: string;
  imgClassName?: string;
  /** Scale up and nudge upward so the glyph overflows the circle top. */
  overflowTop?: boolean;
  alt?: string;
}) {
  if (isCategoryIconUrl(icon)) {
    const imgSize = overflowTop ? Math.round(size * 1.55) : size;
    return (
      // eslint-disable-next-line @next/next/no-img-element -- dynamic category CDN/local URLs
      <img
        src={icon!}
        alt={alt}
        width={imgSize}
        height={imgSize}
        className={cn(
          "pointer-events-none select-none object-contain",
          overflowTop && "-translate-y-[18%] drop-shadow-[0_6px_12px_rgba(0,0,0,0.28)]",
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
