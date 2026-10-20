import type { ImgHTMLAttributes } from "react";
import { resolveCategoryIconSources } from "@/config/category-icon-delivery";

type CuratedCategoryIconImgProps = ImgHTMLAttributes<HTMLImageElement> & {
  src: string;
};

/**
 * Static category PNG with optional WebP `<picture>` when flag on and asset is allowlisted.
 * Preserves baseline `<img>` attributes when WebP is not active (no implicit lazy/priority).
 */
export function CuratedCategoryIconImg({
  src,
  alt = "",
  width,
  height,
  className,
  style,
  loading,
  fetchPriority,
  decoding,
  draggable,
  ...rest
}: CuratedCategoryIconImgProps) {
  const sources = resolveCategoryIconSources(src);
  const common = {
    alt,
    width,
    height,
    className,
    style,
    draggable,
    ...rest,
  };

  if (!sources) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- curated / static public URLs
      <img src={src} {...common} />
    );
  }

  const img = (
    // eslint-disable-next-line @next/next/no-img-element -- PNG fallback for allowlisted WebP
    <img
      src={sources.png}
      {...common}
      loading={loading}
      fetchPriority={fetchPriority}
      decoding={decoding ?? "async"}
    />
  );

  return (
    <picture>
      <source type="image/webp" srcSet={sources.webp} />
      {img}
    </picture>
  );
}
