"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { SafeImage } from "@/components/ui/safe-image";
import { resolveBrandLogoUrl } from "@/config/brand-logos";
import { cn } from "@/lib/utils";
import type { Brand } from "@/types/category";
import type { BrandBrief } from "@/types/product";

/**
 * Brand mark for PDP — prefers API/local logo, degrades to typographic mark.
 * `quiet` density sits under title/buy box (not hero chrome).
 */
export function PdpBrandMark({
  brand,
  logoUrl,
  className,
  animate = true,
  density = "default",
}: {
  brand: BrandBrief;
  /** Full brand row logo when available from brands list. */
  logoUrl?: string | null;
  className?: string;
  animate?: boolean;
  density?: "default" | "quiet";
}) {
  const reduced = useReducedMotion();
  const quiet = density === "quiet";
  const href = brand.slug?.trim()
    ? `/brands/${brand.slug.trim()}`
    : `/catalog?brand=${brand.id}`;
  const resolved = resolveBrandLogoUrl(brand.name, logoUrl);
  const isSvg = Boolean(resolved?.toLowerCase().includes(".svg"));
  const initial = (brand.name || "B").trim().slice(0, 1);

  const inner = (
    <Link
      href={href}
      className={cn(
        "group inline-flex max-w-full items-center outline-none",
        quiet ? "gap-2.5" : "gap-3",
        "focus-visible:rounded-xl focus-visible:ring-2 focus-visible:ring-primary/35 focus-visible:ring-offset-2",
        className,
      )}
      aria-label={`برند ${brand.name}`}
    >
      <span
        className={cn(
          "relative grid shrink-0 place-items-center overflow-hidden bg-white",
          "ring-1 ring-steel/10 transition-transform duration-300 group-hover:scale-[1.02]",
          quiet
            ? "h-9 w-9 rounded-lg shadow-none sm:h-10 sm:w-10"
            : "h-12 w-12 rounded-xl shadow-[0_6px_18px_rgba(94,95,94,0.12)] sm:h-14 sm:w-14",
        )}
      >
        {resolved ? (
          <SafeImage
            src={resolved}
            alt=""
            fill
            sizes={quiet ? "40px" : "56px"}
            className={cn("object-contain", quiet ? "p-1.5" : "p-2.5")}
            unoptimized={isSvg}
            fallback={
              <span
                className={cn(
                  "font-bold text-steel/35",
                  quiet ? "text-sm" : "text-lg",
                )}
              >
                {initial}
              </span>
            }
          />
        ) : (
          <span
            className={cn(
              "font-bold text-steel/35",
              quiet ? "text-sm" : "text-lg",
            )}
          >
            {initial}
          </span>
        )}
      </span>
      <span className="min-w-0 text-start">
        {quiet ? (
          <>
            <span className="block text-[11px] font-medium text-steel/80">برند</span>
            <span className="mt-0.5 block truncate text-sm font-semibold tracking-tight text-foreground transition-colors group-hover:text-primary">
              {brand.name}
              {brand.country ? (
                <span className="font-medium text-steel"> · {brand.country}</span>
              ) : null}
            </span>
          </>
        ) : (
          <>
            <span className="block truncate text-sm font-bold tracking-tight text-foreground transition-colors group-hover:text-primary sm:text-[15px]">
              {brand.name}
            </span>
            {brand.country ? (
              <span className="mt-0.5 block truncate text-[11px] font-medium text-steel">
                {brand.country}
              </span>
            ) : (
              <span className="mt-0.5 block text-[11px] font-medium text-steel/70">
                صفحه برند
              </span>
            )}
          </>
        )}
      </span>
    </Link>
  );

  if (!animate || reduced) return inner;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
    >
      {inner}
    </motion.div>
  );
}

export function findBrandLogoUrl(
  brand: BrandBrief | null | undefined,
  brands: Brand[],
): string | null {
  if (!brand) return null;
  const full = brands.find((b) => b.id === brand.id);
  return resolveBrandLogoUrl(brand.name, full?.logo_url ?? null);
}
