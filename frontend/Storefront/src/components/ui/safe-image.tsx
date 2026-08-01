"use client";

import { useState, type ReactNode } from "react";
import Image, { type ImageProps } from "next/image";
import { toSafeNextImageSrc } from "@/lib/image-remote-patterns";

type SafeImageProps = Omit<ImageProps, "src"> & {
  src: ImageProps["src"];
  /** Rendered when src is unconfigured / blocked or the image fails to load. */
  fallback?: ReactNode;
};

/**
 * next/image wrapper that never throws on unconfigured remote hosts.
 * Invalid / blocked URLs (e.g. picsum.photos) fall back instead of error-boundary.
 */
export function SafeImage({ src, fallback = null, onError, unoptimized, ...rest }: SafeImageProps) {
  const resolved = typeof src === "string" ? toSafeNextImageSrc(src) : src;
  const [failed, setFailed] = useState(false);

  if (resolved == null || resolved === "" || failed) {
    return <>{fallback}</>;
  }

  const srcStr = typeof resolved === "string" ? resolved : null;
  const isSvg = Boolean(srcStr?.toLowerCase().includes(".svg"));

  return (
    <Image
      {...rest}
      src={resolved}
      unoptimized={unoptimized ?? isSvg}
      onError={(e) => {
        setFailed(true);
        onError?.(e);
      }}
    />
  );
}
