"use client";

import type { ComponentType, ImgHTMLAttributes } from "react";
import * as Icons from "react-iconly";
import { Category as CategoryIcon } from "react-iconly";
import {
  categoryIconWebpExperimentEnabled,
  resolveCategoryIconSources,
} from "@/config/category-icon-delivery";
import { isCategoryIconUrl } from "@/config/category-icons";
import { cn } from "@/lib/utils";

type IconlyProps = {
  size?: number | string;
  set?: string;
  primaryColor?: string;
  stroke?: string;
};

type DockPriorityProps = {
  /** Only applied when WebP experiment is enabled (hero dock). */
  loading?: ImgHTMLAttributes<HTMLImageElement>["loading"];
  fetchPriority?: "high" | "low" | "auto";
};

function CategoryIconImage({
  src,
  webpSrc,
  alt,
  imgSize,
  className,
  style,
  useWebpDelivery,
  loading,
  fetchPriority,
}: {
  src: string;
  webpSrc?: string | null;
  alt: string;
  imgSize: number;
  className?: string;
  style?: React.CSSProperties;
  useWebpDelivery: boolean;
  loading?: ImgHTMLAttributes<HTMLImageElement>["loading"];
  fetchPriority?: "high" | "low" | "auto";
}) {
  if (!useWebpDelivery || !webpSrc) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- baseline-compatible when flag off
      <img
        src={src}
        alt={alt}
        width={imgSize}
        height={imgSize}
        className={className}
        style={style}
        draggable={false}
      />
    );
  }

  const img = (
    // eslint-disable-next-line @next/next/no-img-element -- allowlisted WebP experiment
    <img
      src={src}
      alt={alt}
      width={imgSize}
      height={imgSize}
      className={className}
      style={style}
      draggable={false}
      loading={loading}
      fetchPriority={fetchPriority}
      decoding="async"
    />
  );

  return (
    <picture>
      <source type="image/webp" srcSet={webpSrc} />
      {img}
    </picture>
  );
}

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
  overflowScale = 2.015,
  alt = "",
  loading,
  fetchPriority,
}: {
  icon?: string | null;
  size?: number;
  color?: string;
  className?: string;
  imgClassName?: string;
  overflowTop?: boolean;
  overflowScale?: number;
  alt?: string;
} & DockPriorityProps) {
  if (isCategoryIconUrl(icon)) {
    const sources = resolveCategoryIconSources(icon!);
    const useWebpDelivery = Boolean(sources);
    const pngSrc = sources?.png ?? icon!;
    const webpSrc = sources?.webp ?? null;
    const webpOn = categoryIconWebpExperimentEnabled();
    const dockLoading = webpOn && useWebpDelivery ? loading : undefined;
    const dockPriority = webpOn && useWebpDelivery ? fetchPriority : undefined;

    const imgSize = overflowTop ? Math.round(size * overflowScale) : size;
    const imgClass = cn(
      overflowTop
        ? "mx-auto block select-none object-contain object-center"
        : "pointer-events-none mx-auto block select-none object-contain object-center",
      overflowTop && "-translate-y-[8%] drop-shadow-[0_6px_12px_rgba(0,0,0,0.28)]",
      imgClassName,
      !overflowTop ? className : undefined,
    );
    const imgStyle = { width: imgSize, height: imgSize, maxWidth: "none" as const };

    if (overflowTop) {
      return (
        <span
          className={cn(
            "pointer-events-none absolute inset-0 flex items-center justify-center overflow-visible",
            className,
          )}
          aria-hidden={alt ? undefined : true}
        >
          <CategoryIconImage
            src={pngSrc}
            webpSrc={webpSrc}
            alt={alt}
            imgSize={imgSize}
            className={imgClass}
            style={imgStyle}
            useWebpDelivery={useWebpDelivery}
            loading={dockLoading}
            fetchPriority={dockPriority}
          />
        </span>
      );
    }
    return (
      <CategoryIconImage
        src={pngSrc}
        webpSrc={webpSrc}
        alt={alt}
        imgSize={imgSize}
        className={cn(imgClass, className)}
        style={imgStyle}
        useWebpDelivery={useWebpDelivery}
        loading={dockLoading}
        fetchPriority={dockPriority}
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
