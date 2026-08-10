import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type = "text", ...props }, ref) => (
  <input
    ref={ref}
    type={type}
    className={cn(
      /* text-base (≥16px) avoids iOS focus zoom on mobile forms */
      "h-11 w-full rounded-xl bg-input px-4 text-base text-foreground shadow-soft outline-none transition-shadow placeholder:text-muted-foreground focus:ring-2 focus:ring-ring/40",
      className,
    )}
    {...props}
  />
));
Input.displayName = "Input";
