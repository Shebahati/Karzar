import { getImageProps } from "next/image";
import type { CSSProperties, ReactNode } from "react";
import { SafeImage } from "@/components/ui/safe-image";
import { HERO_IMAGE_QUALITY } from "@/lib/cwv";

/** Intrinsic sizes for v2 hero art (Next image optimizer input dimensions). */
const HERO_DESKTOP_INTRINSIC = { width: 1672, height: 941 } as const;
const HERO_MOBILE_INTRINSIC = { width: 941, height: 1672 } as const;

export type HeroBackgroundPictureSources = {
  desktop: Pick<
    ReturnType<typeof getImageProps>["props"],
    "src" | "srcSet" | "sizes"
  >;
  mobileSrcSet: string;
};

type BuildHeroBackgroundPictureSourcesArgs = {
  desktopSrc: string;
  mobileSrc?: string | null;
  priority?: boolean;
};

/** Build optimized `/_next/image` srcsets for art-directed hero backgrounds. */
export function buildHeroBackgroundPictureSources({
  desktopSrc,
  mobileSrc,
  priority = false,
}: BuildHeroBackgroundPictureSourcesArgs): HeroBackgroundPictureSources | null {
  if (!mobileSrc) return null;

  const perf = priority
    ? { priority: true as const, fetchPriority: "high" as const }
    : { loading: "lazy" as const };

  const desktop = getImageProps({
    src: desktopSrc,
    alt: "",
    ...HERO_DESKTOP_INTRINSIC,
    sizes: "(max-width: 1024px) 100vw, 100vw",
    quality: HERO_IMAGE_QUALITY,
    ...perf,
  });

  const mobile = getImageProps({
    src: mobileSrc,
    alt: "",
    ...HERO_MOBILE_INTRINSIC,
    sizes: "100vw",
    quality: HERO_IMAGE_QUALITY,
    ...perf,
  });

  const { src, srcSet, sizes } = desktop.props;
  if (!srcSet || !mobile.props.srcSet) return null;

  return {
    desktop: { src, srcSet, sizes },
    mobileSrcSet: mobile.props.srcSet,
  };
}

type HeroBackgroundImageProps = {
  desktopSrc: string;
  mobileSrc?: string | null;
  focal?: string;
  priority?: boolean;
  sizes?: string;
  className?: string;
  style?: CSSProperties;
  fallback?: ReactNode;
};

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
  className,
  style,
  fallback,
}: HeroBackgroundImageProps) {
  const picture = buildHeroBackgroundPictureSources({
    desktopSrc,
    mobileSrc,
    priority,
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
        {...(priority
          ? { priority: true, fetchPriority: "high" as const, quality: HERO_IMAGE_QUALITY }
          : { loading: "lazy" as const, quality: HERO_IMAGE_QUALITY })}
      />
    );
  }

  const { desktop, mobileSrcSet } = picture;

  return (
    <picture className="absolute inset-0 block">
      <source media="(max-width: 767px)" srcSet={mobileSrcSet} />
      <img
        src={desktop.src}
        srcSet={desktop.srcSet}
        sizes={desktop.sizes}
        alt=""
        decoding={priority ? "sync" : "async"}
        fetchPriority={priority ? "high" : "auto"}
        loading={priority ? "eager" : "lazy"}
        className={className ?? "absolute inset-0 h-full w-full object-cover"}
        style={objectStyle}
      />
    </picture>
  );
}
