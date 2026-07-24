import Image from "next/image";
import Link from "next/link";
import { cn } from "@/lib/utils";

export type LogoVariant = "icon" | "mark" | "slogan";

const ASSETS: Record<
  LogoVariant,
  { src: string; width: number; height: number; alt: string }
> = {
  /** Square K mark — favicon / compact chrome. */
  icon: {
    src: "/images/brand/icon.svg",
    width: 40,
    height: 40,
    alt: "کارزار",
  },
  /** Horizontal wordmark without slogan. */
  mark: {
    src: "/images/brand/logo.svg",
    width: 168,
    height: 30,
    alt: "کارزار",
  },
  /** Horizontal wordmark + Cutting Tools slogan — large surfaces only. */
  slogan: {
    src: "/images/brand/logo-slogan.svg",
    width: 220,
    height: 55,
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
}: {
  className?: string;
  variant?: LogoVariant;
  href?: string | null;
  priority?: boolean;
  /** Override display height (width scales from intrinsic aspect). */
  height?: number;
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
      className="object-contain object-center"
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
