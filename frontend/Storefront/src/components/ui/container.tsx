import * as React from "react";
import { cn } from "@/lib/utils";

/** Centered max-width wrapper with responsive inline padding. */
export function Container({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("mx-auto w-full max-w-[1320px] px-5 sm:px-6 lg:px-8", className)}
      {...props}
    />
  );
}
