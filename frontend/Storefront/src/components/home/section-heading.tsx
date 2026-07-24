"use client";

import Link from "next/link";
import { ChevronLeft } from "react-iconly";
import { cn } from "@/lib/utils";

export function SectionHeading({
  title,
  subtitle,
  href,
  hrefLabel = "مشاهده همه",
  className,
}: {
  title: string;
  subtitle?: string;
  href?: string;
  hrefLabel?: string;
  className?: string;
}) {
  return (
    <div className={cn("mb-5 flex items-end justify-between gap-4 sm:mb-6", className)}>
      <div>
        <div className="flex items-center gap-2.5">
          <span className="h-6 w-1.5 rounded-full bg-primary" aria-hidden />
          <h2 className="text-lg font-bold text-foreground sm:text-2xl">{title}</h2>
        </div>
        {subtitle && (
          <p className="mt-1.5 ps-4 text-xs leading-6 text-muted-foreground sm:text-sm">
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
