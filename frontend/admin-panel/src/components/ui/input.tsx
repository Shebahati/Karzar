import * as React from "react";

import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

/**
 * Borderless input: a soft muted surface with a focus ring instead of a hard
 * border. `invalid` styling is driven by the `aria-invalid` attribute so
 * react-hook-form error states wire up with no extra props.
 */
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        className={cn(
          "flex h-11 w-full rounded-lg bg-input px-4 py-2 text-sm text-foreground shadow-soft transition-all duration-200 placeholder:text-muted-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:bg-card",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "aria-[invalid=true]:ring-2 aria-[invalid=true]:ring-destructive/50",
          "file:border-0 file:bg-transparent file:text-sm file:font-medium",
          className,
        )}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export { Input };
