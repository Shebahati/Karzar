"use client";

import type { ReactNode } from "react";
import { cn, toPersianDigits } from "@/lib/utils";

interface FaNumProps {
  children: ReactNode;
  className?: string;
}

/** Renders text with Western digits converted to Persian. */
export function FaNum({ children, className }: FaNumProps) {
  if (children === null || children === undefined) return null;

  if (typeof children === "string" || typeof children === "number") {
    return (
      <span className={cn("tnum", className)} dir="rtl">
        {toPersianDigits(children)}
      </span>
    );
  }

  return <span className={className}>{children}</span>;
}
