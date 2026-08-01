import Image from "next/image";
import Link from "next/link";
import { cn } from "@/lib/utils";

export type LogoVariant = "icon" | "mark" | "slogan";

const ASSETS: Record<
  LogoVariant,
  { src: string; width: number; height: number; alt: string }
> = {
  /** Chevron mark — favicon / compact chrome. */
  icon: {
    src: "/images/brand/icon.svg",
    width: 118,
    height: 105,
    alt: "کارزار",
  },
  /** Horizontal wordmark without slogan. */
  mark: {
    src: "/images/brand/logo.svg",
    width: 663,
    height: 105,
    alt: "کارزار",
  },
  /** Horizontal wordmark + Cutting Tools slogan — large surfaces only. */
  slogan: {
    src: "/images/brand/logo-slogan.svg",
    width: 663,
    height: 105,
    alt: "کارزار — Cutting Tools",
  },
};

/**
 * Brand logo. Prefer `mark` in chrome, `slogan` in heroes/footers,
 * `icon` where only the K glyph fits.
 */
export function Logo({
  className,
  variant = "mark",
  href = "/",
  priority = false,
  height,
  tone = "brand",
}: {
  className?: string;
  variant?: LogoVariant;
  href?: string | null;
  priority?: boolean;
  /** Override display height (width scales from intrinsic aspect). */
  height?: number;
  /** `onDark` forces a white mark for contrast over hero/media. */
  tone?: "brand" | "onDark";
}) {
  const asset = ASSETS[variant];
  const displayHeight = height ?? (variant === "icon" ? 36 : variant === "slogan" ? 44 : 28);
  const displayWidth = Math.round((asset.width / asset.height) * displayHeight);

  const img = (
    <Image
      src={asset.src}
      alt={asset.alt}
      width={displayWidth}
      height={displayHeight}
      priority={priority}
      unoptimized
      className={cn(
        "object-contain object-center transition-[filter] duration-300",
        tone === "onDark" && "brightness-0 invert",
      )}
    />
  );

  if (href === null) {
    return <span className={cn("inline-flex items-center", className)}>{img}</span>;
  }

  return (
    <Link
      href={href}
      className={cn("inline-flex items-center", className)}
      aria-label="کارزار"
    >
      {img}
    </Link>
  );
}
