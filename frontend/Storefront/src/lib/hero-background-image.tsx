"use client";

import { getImageProps } from "next/image";
import { useState, type CSSProperties, type ReactNode } from "react";
import { SafeImage } from "@/components/ui/safe-image";
import { HERO_IMAGE_QUALITY } from "@/lib/cwv";
import { DEFAULT_MOBILE_SOURCE_MAX_PX } from "@/lib/hero-campaign-layout";
import { cn } from "@/lib/utils";

/** Legacy v2 / pre-calibrated hero art passed to the Next image optimizer. */
const LEGACY_HERO_DESKTOP_INTRINSIC = { width: 1672, height: 941 } as const;
const LEGACY_HERO_MOBILE_INTRINSIC = { width: 1280, height: 720 } as const;

/** Calibrated campaign masters. Optimizer srcsets still follow `deviceSizes`. */
export const CALIBRATED_HERO_DESKTOP_INTRINSIC = { width: 3840, height: 2160 } as const;
export const CALIBRATED_HERO_MOBILE_INTRINSIC = { width: 2880, height: 2160 } as const;

const CALIBRATED_HERO_DIR = "/images/hero/reborn-5/calibrated-20261018/";

export function heroIntrinsicSize(
  src: string,
  kind: "desktop" | "mobile",
): { width: number; height: number } {
  if (src.includes(CALIBRATED_HERO_DIR)) {
    return kind === "desktop"
      ? CALIBRATED_HERO_DESKTOP_INTRINSIC
      : CALIBRATED_HERO_MOBILE_INTRINSIC;
  }
  return kind === "desktop" ? LEGACY_HERO_DESKTOP_INTRINSIC : LEGACY_HERO_MOBILE_INTRINSIC;
}

export type HeroBackgroundPictureSources = {
  desktop: Pick<
    ReturnType<typeof getImageProps>["props"],
    "src" | "srcSet" | "sizes" | "width" | "height" | "decoding" | "fetchPriority"
  >;
  mobileSrcSet: string;
  loading: "eager" | "lazy";
};

type BuildHeroBackgroundPictureSourcesArgs = {
  desktopSrc: string;
  mobileSrc?: string | null;
  priority?: boolean;
  sizes?: string;
};

/** Build optimized `/_next/image` srcsets for art-directed hero backgrounds. */
export function buildHeroBackgroundPictureSources({
  desktopSrc,
  mobileSrc,
  priority = false,
  sizes = "(max-width: 1024px) 100vw, 100vw",
}: BuildHeroBackgroundPictureSourcesArgs): HeroBackgroundPictureSources | null {
  if (!mobileSrc) return null;

  const perf = priority
    ? { priority: true as const, fetchPriority: "high" as const }
    : { loading: "lazy" as const };

  const desktop = getImageProps({
    src: desktopSrc,
    alt: "",
    ...heroIntrinsicSize(desktopSrc, "desktop"),
    sizes,
    quality: HERO_IMAGE_QUALITY,
    ...perf,
  });

  const mobile = getImageProps({
    src: mobileSrc,
    alt: "",
    ...heroIntrinsicSize(mobileSrc, "mobile"),
    sizes: "100vw",
    quality: HERO_IMAGE_QUALITY,
    ...perf,
  });

  const {
    src,
    srcSet,
    sizes: desktopSizes,
    width,
    height,
    decoding,
    fetchPriority,
  } = desktop.props;
  if (!srcSet || !mobile.props.srcSet) return null;

  return {
    desktop: { src, srcSet, sizes: desktopSizes, width, height, decoding, fetchPriority },
    mobileSrcSet: mobile.props.srcSet,
    loading: priority ? "eager" : "lazy",
  };
}

type HeroBackgroundImageProps = {
  desktopSrc: string;
  mobileSrc?: string | null;
  focal?: string;
  priority?: boolean;
  sizes?: string;
  mobileSourceMaxWidthPx?: number;
  className?: string;
  style?: CSSProperties;
  fallback?: ReactNode;
  onLoad?: () => void;
};

type HeroBackgroundPictureProps = {
  picture: HeroBackgroundPictureSources;
  mobileSourceMaxWidthPx: number;
  className?: string;
  style: CSSProperties;
  fallback?: ReactNode;
  onLoad?: () => void;
};

function HeroBackgroundPicture({
  picture,
  mobileSourceMaxWidthPx,
  className,
  style,
  fallback = null,
  onLoad,
}: HeroBackgroundPictureProps) {
  const [failed, setFailed] = useState(false);
  const { desktop, mobileSrcSet, loading } = picture;

  if (failed) {
    return <>{fallback}</>;
  }

  return (
    <picture className="absolute inset-0 block">
      <source media={`(max-width: ${mobileSourceMaxWidthPx}px)`} srcSet={mobileSrcSet} />
      <img
        src={desktop.src}
        srcSet={desktop.srcSet}
        sizes={desktop.sizes}
        width={desktop.width}
        height={desktop.height}
        alt=""
        decoding={desktop.decoding}
        fetchPriority={desktop.fetchPriority}
        loading={loading}
        className={cn("absolute inset-0 h-full w-full object-cover", className)}
        style={style}
        onError={() => setFailed(true)}
        onLoad={onLoad}
      />
    </picture>
  );
}

/**
 * Full-bleed hero background: CSS art direction via `<picture>` with Next-optimized srcsets
 * (avoids raw `/images/hero/...png` on `<source srcSet>`).
 */
export function HeroBackgroundImage({
  desktopSrc,
  mobileSrc,
  focal,
  priority = false,
  sizes = "(max-width: 1024px) 100vw, 100vw",
  mobileSourceMaxWidthPx = DEFAULT_MOBILE_SOURCE_MAX_PX,
  className,
  style,
  fallback,
  onLoad,
}: HeroBackgroundImageProps) {
  const picture = buildHeroBackgroundPictureSources({
    desktopSrc,
    mobileSrc,
    priority,
    sizes,
  });

  const objectStyle: CSSProperties = {
    objectPosition: focal || "center",
    ...style,
  };

  if (!picture) {
    return (
      <SafeImage
        src={desktopSrc}
        alt=""
        fill
        sizes={sizes}
        className={className ?? "object-cover"}
        style={objectStyle}
        fallback={fallback}
        onLoad={onLoad}
        {...(priority
          ? { priority: true, fetchPriority: "high" as const, quality: HERO_IMAGE_QUALITY }
          : { loading: "lazy" as const, quality: HERO_IMAGE_QUALITY })}
      />
    );
  }

  return (
    <HeroBackgroundPicture
      picture={picture}
      mobileSourceMaxWidthPx={mobileSourceMaxWidthPx}
      className={className}
      style={objectStyle}
      fallback={fallback}
      onLoad={onLoad}
    />
  );
}
