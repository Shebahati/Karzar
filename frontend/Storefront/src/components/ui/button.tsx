import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Shared Storefront button — soft brand-tinted hover (red/steel), never a white
 * flood. `hover-fine` avoids sticky glow on touch; `motion-reduce` skips lift/scale.
 */
const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium",
    "transition-[background-color,color,box-shadow,transform,opacity,border-color] duration-300 ease-out",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-0",
    "disabled:pointer-events-none disabled:opacity-50",
    "motion-safe:active:scale-[0.98] active:shadow-none",
    "motion-reduce:transition-[background-color,color,box-shadow,opacity,border-color] motion-reduce:duration-150",
  ].join(" "),
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-primary-foreground shadow-btn-rest hover-fine:bg-karzar-600 hover-fine:shadow-btn-primary motion-safe:hover-fine:-translate-y-px",
        outline:
          "bg-transparent text-foreground ring-1 ring-inset ring-border hover-fine:bg-steel/[0.06] hover-fine:text-foreground hover-fine:ring-steel/28 hover-fine:shadow-btn-steel motion-safe:hover-fine:-translate-y-px",
        ghost:
          "bg-transparent text-foreground hover-fine:bg-steel/[0.08] hover-fine:text-foreground hover-fine:shadow-btn-ghost",
        soft:
          "bg-white text-foreground shadow-btn-rest ring-1 ring-inset ring-steel/10 hover-fine:bg-karzar-50 hover-fine:text-karzar-700 hover-fine:ring-primary/22 hover-fine:shadow-btn-soft motion-safe:hover-fine:-translate-y-px",
        muted:
          "bg-secondary text-secondary-foreground shadow-btn-rest hover-fine:bg-steel/[0.11] hover-fine:text-foreground hover-fine:shadow-btn-steel motion-safe:hover-fine:-translate-y-px",
        destructive:
          "bg-destructive text-destructive-foreground shadow-btn-rest hover-fine:opacity-90 hover-fine:shadow-btn-primary motion-safe:hover-fine:-translate-y-px",
      },
      size: {
        sm: "h-9 px-4",
        md: "h-11 px-6",
        lg: "h-13 px-8 text-base",
        icon: "h-11 w-11",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";

export { buttonVariants };
