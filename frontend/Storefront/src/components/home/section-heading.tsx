"use client";

import Link from "next/link";
import { ChevronLeft } from "react-iconly";
import { cn } from "@/lib/utils";

/**
 * Standard home section title row.
 * Discount / deal carousels use the composed lead promo in `ProductCarousel` instead —
 * do not reintroduce badge / wash chrome here.
 */
export function SectionHeading({
  title,
  subtitle,
  href,
  hrefLabel = "مشاهده همه",
  className,
  id,
  iconSrc,
}: {
  title: string;
  subtitle?: string;
  href?: string;
  hrefLabel?: string;
  className?: string;
  id?: string;
  /** Optional leading icon (e.g. category PNG). */
  iconSrc?: string;
}) {
  return (
    <div className={cn("mb-5 flex items-end justify-between gap-4 sm:mb-6", className)}>
      <div>
        <div className="flex items-center gap-2.5">
          {iconSrc ? (
            <span
              className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-secondary/80 sm:h-10 sm:w-10"
              aria-hidden
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- static public icon URL */}
              <img
                src={iconSrc}
                alt=""
                width={28}
                height={28}
                className="h-6 w-6 object-contain sm:h-7 sm:w-7"
              />
            </span>
          ) : (
            <span className="h-6 w-1.5 rounded-full bg-primary" aria-hidden />
          )}
          <h2 id={id} className="type-section text-foreground">
            {title}
          </h2>
        </div>
        {subtitle && (
          <p
            className={cn(
              "type-lede mt-1.5 text-muted-foreground",
              iconSrc ? "ps-11 sm:ps-12" : "ps-4",
            )}
          >
            {subtitle}
          </p>
        )}
      </div>

      {href && (
        <Link
          href={href}
          className="group flex shrink-0 items-center gap-1 text-xs font-bold text-primary sm:text-sm"
        >
          {hrefLabel}
          <ChevronLeft size="small" set="light" />
        </Link>
      )}
    </div>
  );
}
