import * as React from "react";
import { cn } from "@/lib/utils";

/** Elevated, borderless surface — the storefront's primary container. */
export const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-2xl bg-card text-card-foreground shadow-card",
      className,
    )}
    {...props}
  />
));
Card.displayName = "Card";
