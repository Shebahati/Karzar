import Image from "next/image";
import { cn } from "@/lib/utils";

/** Karzar chevron mark — compact square chrome (sidebar collapsed state, login card). */
export function LogoMark({ className, size = 24 }: { className?: string; size?: number }) {
  return (
    <Image
      src="/images/brand/icon.svg"
      alt="کارزار"
      width={size}
      height={size}
      unoptimized
      className={cn("shrink-0 object-contain", className)}
    />
  );
}

/** Karzar horizontal wordmark — expanded sidebar / wide chrome. */
export function Logo({ className, height = 22 }: { className?: string; height?: number }) {
  const width = Math.round((663 / 105) * height);
  return (
    <Image
      src="/images/brand/logo.svg"
      alt="کارزار"
      width={width}
      height={height}
      unoptimized
      className={cn("object-contain object-center", className)}
    />
  );
}
